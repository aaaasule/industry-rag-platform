"""M4：用量缓冲 flush、小时聚合与查询 API。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.identity.models import ROLE_MEMBER, Membership, User
from app.modules.modelops.usage_flush import aggregate_hourlies, flush_usage_buffer
from app.modules.modelops.usage_models import LlmUsage, LlmUsageHourly, ModelPricing
from app.modules.modelops.usage_recorder import USAGE_BUFFER_KEY, UsageRecorder
from app.platform.config import get_settings
from app.platform.db import session_scope
from app.platform.ids import uuid7
from app.platform.security import hash_password
from tests.conftest import TEST_PASSWORD, Fixture


async def _login(
    client: AsyncClient, email: str, password: str, tenant_slug: str
) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password, "tenant_slug": tenant_slug},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _migration_session():
    settings = get_settings()
    url = settings.database_migration_url or settings.database_url
    engine = create_async_engine(url, pool_pre_ping=True)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    return engine, maker


async def test_record_flush_aggregate_and_api(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    import redis

    settings = get_settings()
    r = redis.from_url(settings.redis_url, decode_responses=True)
    r.delete(USAGE_BUFFER_KEY)

    engine, maker = await _migration_session()
    try:
        async with maker() as session:
            await session.execute(
                delete(LlmUsageHourly).where(
                    LlmUsageHourly.tenant_id == fixture_data.primary_tenant_id
                )
            )
            await session.execute(
                delete(LlmUsage).where(LlmUsage.tenant_id == fixture_data.primary_tenant_id)
            )
            pricing = (
                await session.execute(
                    select(ModelPricing).where(
                        ModelPricing.provider_type == "fake",
                        ModelPricing.model == "usage-test-model",
                    )
                )
            ).scalar_one_or_none()
            if pricing is None:
                session.add(
                    ModelPricing(
                        id=uuid7(),
                        provider_type="fake",
                        model="usage-test-model",
                        prompt_price_per_1k=Decimal("1.000000"),
                        completion_price_per_1k=Decimal("2.000000"),
                        currency="USD",
                        effective_from=datetime(2020, 1, 1, tzinfo=UTC),
                    )
                )
            await session.commit()
    finally:
        await engine.dispose()

    await UsageRecorder.record(
        tenant_id=fixture_data.primary_tenant_id,
        user_id=fixture_data.user_id,
        purpose="chat",
        provider_type="fake",
        model="usage-test-model",
        prompt_tokens=1000,
        completion_tokens=500,
        latency_ms=42,
        success=True,
    )
    written = await flush_usage_buffer()
    assert written >= 1

    async with session_scope(
        tenant_id=fixture_data.primary_tenant_id, user_id=fixture_data.user_id
    ) as session:
        rows = list(
            (
                await session.execute(
                    select(LlmUsage).where(LlmUsage.tenant_id == fixture_data.primary_tenant_id)
                )
            )
            .scalars()
            .all()
        )
        assert rows
        latest = max(rows, key=lambda u: u.created_at)
        assert latest.prompt_tokens == 1000
        assert latest.completion_tokens == 500
        assert latest.cost == Decimal("2.000000")  # 1*1 + 0.5*2

    buckets = await aggregate_hourlies(lookback_hours=48)
    assert buckets >= 1

    summary = await client.get(
        "/api/v1/usages/summary",
        headers=auth_headers,
        params={"period": "month", "timezone": "Asia/Shanghai"},
    )
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["call_count"] >= 1
    assert body["total_tokens"] >= 1500

    now = datetime.now(UTC)
    series = await client.get(
        "/api/v1/usages/series",
        headers=auth_headers,
        params={
            "from": (now - timedelta(days=1)).isoformat(),
            "to": (now + timedelta(hours=1)).isoformat(),
            "timezone": "Asia/Shanghai",
            "granularity": "day",
            "group_by": "purpose",
        },
    )
    assert series.status_code == 200, series.text
    series_body = series.json()
    assert series_body["series"]
    # hourlies 聚合后应带回 latency_p95_ms（可为 int）
    first_points = series_body["series"][0]["points"]
    assert first_points
    assert "latency_p95_ms" in first_points[0]

    breakdown = await client.get(
        "/api/v1/usages/breakdown",
        headers=auth_headers,
        params={
            "from": (now - timedelta(days=1)).isoformat(),
            "to": (now + timedelta(hours=1)).isoformat(),
            "dimension": "purpose",
            "metric": "call_count",
        },
    )
    assert breakdown.status_code == 200, breakdown.text
    assert breakdown.json()["total"] >= 1

    by_user = await client.get(
        "/api/v1/usages/breakdown",
        headers=auth_headers,
        params={
            "from": (now - timedelta(days=1)).isoformat(),
            "to": (now + timedelta(hours=1)).isoformat(),
            "dimension": "user",
            "metric": "cost",
        },
    )
    assert by_user.status_code == 200, by_user.text
    assert by_user.json()["total"] >= 0
    assert by_user.json()["items"] or by_user.json()["total"] == 0


async def test_member_cannot_query_usages(client: AsyncClient, fixture_data: Fixture) -> None:
    email = f"usage-m-{uuid.uuid4().hex[:8]}@example.com"
    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        user = User(
            email=email,
            display_name="成员",
            password_hash=hash_password(TEST_PASSWORD),
        )
        session.add(user)
        await session.flush()
        session.add(
            Membership(
                tenant_id=fixture_data.primary_tenant_id,
                user_id=user.id,
                role=ROLE_MEMBER,
            )
        )
        uid = user.id

    headers = await _login(client, email, TEST_PASSWORD, fixture_data.primary_tenant_slug)
    resp = await client.get(
        "/api/v1/usages/summary",
        headers=headers,
        params={"timezone": "Asia/Shanghai"},
    )
    assert resp.status_code == 403, resp.text

    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        await session.execute(delete(Membership).where(Membership.user_id == uid))
    async with session_scope() as session:
        await session.execute(delete(User).where(User.id == uid))


async def test_record_swallows_errors(fixture_data: Fixture, monkeypatch) -> None:
    def boom(*_a, **_k):
        raise RuntimeError("redis down")

    monkeypatch.setattr(
        "app.modules.modelops.usage_recorder.aioredis.from_url",
        boom,
    )
    await UsageRecorder.record(
        tenant_id=fixture_data.primary_tenant_id,
        purpose="chat",
        provider_type="fake",
        model="x",
        latency_ms=1,
        success=True,
    )
