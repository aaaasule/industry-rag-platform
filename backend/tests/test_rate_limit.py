"""M4：用户 QPS 与租户 chat 并发限流。"""

from __future__ import annotations

import uuid

import redis
from httpx import AsyncClient

from app.platform.config import get_settings
from app.platform.errors import RateLimited
from app.platform.rate_limit import RateLimiter
from tests.conftest import Fixture


def _redis() -> redis.Redis:
    return redis.from_url(get_settings().redis_url, decode_responses=True)


def _clear_rl_keys(tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
    r = _redis()
    for route in ("chat", "search"):
        r.delete(f"irp:rl:qps:{tenant_id}:{user_id}:{route}")
    r.delete(f"irp:rl:inflight:{tenant_id}:chat")
    for key in r.scan_iter(match=f"irp:rl:lease:{tenant_id}:*"):
        r.delete(key)


def test_qps_limiter_blocks_after_limit(monkeypatch) -> None:
    get_settings.cache_clear()
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_user_per_minute", 2)
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    _clear_rl_keys(tenant_id, user_id)
    limiter = RateLimiter(settings)
    limiter.check_user_qps(tenant_id=tenant_id, user_id=user_id, route="search")
    limiter.check_user_qps(tenant_id=tenant_id, user_id=user_id, route="search")
    try:
        limiter.check_user_qps(tenant_id=tenant_id, user_id=user_id, route="search")
        raise AssertionError("expected RateLimited")
    except RateLimited as exc:
        assert exc.retry_after_seconds >= 1
        assert exc.details.get("route") == "search"
    finally:
        _clear_rl_keys(tenant_id, user_id)


def test_concurrency_limiter_acquire_release(monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_tenant_chat_concurrency", 1)
    tenant_id = uuid.uuid4()
    _clear_rl_keys(tenant_id, uuid.uuid4())
    limiter = RateLimiter(settings)
    lease1 = limiter.acquire_chat_slot(tenant_id=tenant_id)
    assert lease1 is not None
    try:
        limiter.acquire_chat_slot(tenant_id=tenant_id)
        raise AssertionError("expected RateLimited")
    except RateLimited as exc:
        assert exc.details.get("kind") == "concurrency"
    limiter.release_chat_slot(tenant_id=tenant_id, lease_id=lease1)
    lease2 = limiter.acquire_chat_slot(tenant_id=tenant_id)
    assert lease2 is not None
    limiter.release_chat_slot(tenant_id=tenant_id, lease_id=lease2)
    _clear_rl_keys(tenant_id, uuid.uuid4())


async def test_search_rate_limited_returns_429(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture, monkeypatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_user_per_minute", 1)
    _clear_rl_keys(fixture_data.primary_tenant_id, fixture_data.user_id)

    body = {
        "query": "限流测试",
        "kb_ids": [],
        "top_k": 3,
        "options": {},
    }
    first = await client.post("/api/v1/search", headers=auth_headers, json=body)
    # 无 KB 可能 400/空结果；只要不是 429
    assert first.status_code != 429, first.text

    second = await client.post("/api/v1/search", headers=auth_headers, json=body)
    assert second.status_code == 429, second.text
    err = second.json()["error"]
    assert err["code"] == "rate_limited"
    assert int(second.headers.get("Retry-After", "0")) >= 1

    _clear_rl_keys(fixture_data.primary_tenant_id, fixture_data.user_id)


async def test_chat_concurrency_rate_limited(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture, monkeypatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "rate_limit_tenant_chat_concurrency", 1)
    monkeypatch.setattr(settings, "rate_limit_user_per_minute", 0)  # 关闭 QPS 干扰
    _clear_rl_keys(fixture_data.primary_tenant_id, fixture_data.user_id)

    limiter = RateLimiter(settings)
    held = limiter.acquire_chat_slot(tenant_id=fixture_data.primary_tenant_id)
    assert held is not None
    try:
        resp = await client.post(
            "/api/v1/chat/completions",
            headers=auth_headers,
            json={"message": "并发限流", "kb_ids": [], "options": {}},
        )
        assert resp.status_code == 429, resp.text
        assert resp.json()["error"]["code"] == "rate_limited"
        assert int(resp.headers.get("Retry-After", "0")) >= 1
    finally:
        limiter.release_chat_slot(tenant_id=fixture_data.primary_tenant_id, lease_id=held)
        _clear_rl_keys(fixture_data.primary_tenant_id, fixture_data.user_id)
