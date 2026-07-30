"""M4：接入点健康探测与故障转移。"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import delete

from app.modules.modelops.credentials import encrypt_credential
from app.modules.modelops.models import (
    HEALTH_DOWN,
    HEALTH_HEALTHY,
    HEALTH_UNKNOWN,
    PURPOSE_CHAT,
    ModelConnection,
)
from app.modules.modelops.probe import ProbeResult, probe_connection
from app.modules.modelops.provider_factory import ProviderFactory, clear_provider_cache
from app.platform.config import get_settings
from app.platform.db import session_scope
from app.platform.ids import uuid7
from tests.conftest import Fixture


async def test_manual_test_failure_marks_down(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture, monkeypatch
) -> None:
    created = await client.post(
        "/api/v1/model-connections",
        headers=auth_headers,
        json={
            "name": "将失败的探测点",
            "provider_type": "fake",
            "base_url": "http://localhost",
            "model": "fake-chat",
            "purposes": ["chat"],
            "priority": 50,
            "api_key": "sk-abc",
        },
    )
    assert created.status_code == 201, created.text
    conn_id = created.json()["id"]

    async def boom(_row, *, settings=None):
        return ProbeResult(ok=False, latency_ms=1.0, error_message="simulated")

    monkeypatch.setattr("app.modules.modelops.service.probe_connection", boom)

    tested = await client.post(
        f"/api/v1/model-connections/{conn_id}/test",
        headers=auth_headers,
    )
    assert tested.status_code == 200, tested.text
    assert tested.json()["ok"] is False

    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        row = await session.get(ModelConnection, uuid.UUID(conn_id))
        assert row is not None
        assert row.health == HEALTH_DOWN
        assert row.health_checked_at is not None
        await session.execute(delete(ModelConnection).where(ModelConnection.id == row.id))


async def test_resolve_skips_down_then_env_when_all_down(
    client: AsyncClient,
    fixture_data: Fixture,
) -> None:
    clear_provider_cache()
    settings = get_settings()
    primary = uuid7()
    backup = uuid7()
    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        down = ModelConnection(
            id=primary,
            tenant_id=fixture_data.primary_tenant_id,
            name="主-down",
            provider_type="fake",
            base_url="http://localhost",
            credential_cipher=encrypt_credential("", settings),
            credential_hint="",
            model="fake-primary",
            purposes=[PURPOSE_CHAT],
            priority=1,
            enabled=True,
            health=HEALTH_DOWN,
            version=1,
        )
        ok = ModelConnection(
            id=backup,
            tenant_id=fixture_data.primary_tenant_id,
            name="备-healthy",
            provider_type="fake",
            base_url="http://localhost",
            credential_cipher=encrypt_credential("", settings),
            credential_hint="",
            model="fake-backup",
            purposes=[PURPOSE_CHAT],
            priority=2,
            enabled=True,
            health=HEALTH_HEALTHY,
            version=1,
        )
        session.add_all([down, ok])
        await session.flush()

        factory = ProviderFactory(session, settings)
        conn, source = await factory.resolve_connection("chat", fixture_data.primary_tenant_id)
        assert source == "tenant"
        assert conn is not None
        assert conn.id == backup

        # 候选全为 down → env（mock 列表，避免动平台点与独立 engine）
        down.health = HEALTH_DOWN
        ok.health = HEALTH_DOWN

        async def all_down(*, tenant_id, purpose):
            return [down, ok]

        factory._repo.list_for_purpose = all_down  # type: ignore[method-assign]
        conn2, source2 = await factory.resolve_connection("chat", fixture_data.primary_tenant_id)
        assert conn2 is None
        assert source2 == "env"

        await session.execute(
            delete(ModelConnection).where(ModelConnection.id.in_([primary, backup]))
        )


async def test_unknown_still_routable(client: AsyncClient, fixture_data: Fixture) -> None:
    clear_provider_cache()
    settings = get_settings()
    conn_id = uuid7()
    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        session.add(
            ModelConnection(
                id=conn_id,
                tenant_id=fixture_data.primary_tenant_id,
                name="unknown-ok",
                provider_type="fake",
                base_url="http://localhost",
                credential_cipher=encrypt_credential("", settings),
                credential_hint="",
                model="fake-unknown",
                purposes=[PURPOSE_CHAT],
                priority=1,
                enabled=True,
                health=HEALTH_UNKNOWN,
                version=1,
            )
        )
        await session.flush()
        factory = ProviderFactory(session, settings)
        conn, source = await factory.resolve_connection("chat", fixture_data.primary_tenant_id)
        assert source == "tenant"
        assert conn is not None
        assert conn.id == conn_id
        await session.execute(delete(ModelConnection).where(ModelConnection.id == conn_id))


async def test_probe_connection_success_for_fake(
    client: AsyncClient, fixture_data: Fixture
) -> None:
    settings = get_settings()
    conn_id = uuid7()
    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        row = ModelConnection(
            id=conn_id,
            tenant_id=fixture_data.primary_tenant_id,
            name="probe-fake",
            provider_type="fake",
            base_url="http://localhost",
            credential_cipher=encrypt_credential("", settings),
            credential_hint="",
            model="fake-probe",
            purposes=[PURPOSE_CHAT],
            priority=10,
            enabled=True,
            health=HEALTH_UNKNOWN,
            health_checked_at=None,
            version=1,
        )
        session.add(row)
        await session.flush()
        result = await probe_connection(row, settings=settings)
        assert result.ok is True
        await session.execute(delete(ModelConnection).where(ModelConnection.id == conn_id))


async def test_probe_all_updates_health(monkeypatch) -> None:
    """不连真实库：验证 probe_all 会对结果写 healthy/down 并清缓存。"""
    from datetime import UTC, datetime
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    from app.modules.modelops import health_tasks as ht

    healthy_row = SimpleNamespace(
        id=uuid7(),
        name="ok",
        health=HEALTH_UNKNOWN,
        health_checked_at=None,
        provider_type="fake",
    )
    down_row = SimpleNamespace(
        id=uuid7(),
        name="bad",
        health=HEALTH_UNKNOWN,
        health_checked_at=None,
        provider_type="fake",
    )

    async def fake_probe(row, *, settings=None):
        if row is healthy_row:
            return ProbeResult(ok=True, latency_ms=1.0)
        return ProbeResult(ok=False, latency_ms=2.0, error_message="x")

    session = MagicMock()
    session.commit = AsyncMock()
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [healthy_row, down_row]
    session.execute = AsyncMock(return_value=rows_result)

    class _CM:
        async def __aenter__(self):
            return session

        async def __aexit__(self, *args):
            return None

    maker = MagicMock(return_value=_CM())
    engine = MagicMock()
    engine.dispose = AsyncMock()

    monkeypatch.setattr(ht, "create_async_engine", lambda *a, **k: engine)
    monkeypatch.setattr(ht, "async_sessionmaker", lambda *a, **k: maker)
    monkeypatch.setattr(ht, "probe_connection", fake_probe)
    cleared = {"v": False}
    monkeypatch.setattr(ht, "clear_provider_cache", lambda: cleared.update(v=True))

    counts = await ht.probe_all_connections()
    assert counts == {"probed": 2, "healthy": 1, "down": 1}
    assert healthy_row.health == HEALTH_HEALTHY
    assert down_row.health == HEALTH_DOWN
    assert isinstance(healthy_row.health_checked_at, datetime)
    assert healthy_row.health_checked_at.tzinfo == UTC
    assert cleared["v"] is True
    engine.dispose.assert_awaited()


async def test_routes_api_skips_down(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    clear_provider_cache()
    settings = get_settings()
    down_id = uuid7()
    ok_id = uuid7()
    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        session.add_all(
            [
                ModelConnection(
                    id=down_id,
                    tenant_id=fixture_data.primary_tenant_id,
                    name="routes-down",
                    provider_type="fake",
                    base_url="http://localhost",
                    credential_cipher=encrypt_credential("", settings),
                    credential_hint="",
                    model="m1",
                    purposes=[PURPOSE_CHAT],
                    priority=1,
                    enabled=True,
                    health=HEALTH_DOWN,
                    version=1,
                ),
                ModelConnection(
                    id=ok_id,
                    tenant_id=fixture_data.primary_tenant_id,
                    name="routes-ok",
                    provider_type="fake",
                    base_url="http://localhost",
                    credential_cipher=encrypt_credential("", settings),
                    credential_hint="",
                    model="m2",
                    purposes=[PURPOSE_CHAT],
                    priority=2,
                    enabled=True,
                    health=HEALTH_HEALTHY,
                    version=1,
                ),
            ]
        )

    routes = await client.get("/api/v1/model-connections/routes", headers=auth_headers)
    assert routes.status_code == 200, routes.text
    chat = next(i for i in routes.json()["items"] if i["purpose"] == "chat")
    assert chat["connection_id"] == str(ok_id)

    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        await session.execute(
            delete(ModelConnection).where(ModelConnection.id.in_([down_id, ok_id]))
        )
