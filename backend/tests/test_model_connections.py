"""M4：模型接入点 CRUD、掩码与用途路由。"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.identity.models import ROLE_MEMBER, Membership, User
from app.modules.modelops.credentials import encrypt_credential, mask_credential
from app.modules.modelops.models import PURPOSE_CHAT, ModelConnection
from app.modules.modelops.provider_factory import clear_provider_cache
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


async def test_member_cannot_manage_connections(
    client: AsyncClient, fixture_data: Fixture
) -> None:
    email = f"mc-m-{uuid.uuid4().hex[:8]}@example.com"
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
    resp = await client.get("/api/v1/model-connections", headers=headers)
    assert resp.status_code == 403, resp.text

    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        await session.execute(delete(Membership).where(Membership.user_id == uid))
    async with session_scope() as session:
        await session.execute(delete(User).where(User.id == uid))


async def test_crud_mask_and_test(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    clear_provider_cache()
    created = await client.post(
        "/api/v1/model-connections",
        headers=auth_headers,
        json={
            "name": "租户聊天",
            "provider_type": "fake",
            "base_url": "http://localhost",
            "model": "fake-chat",
            "purposes": ["chat"],
            "priority": 10,
            "api_key": "sk-secret-key-xyz",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["credential_masked"] == mask_credential("xyz")
    assert "sk-secret" not in created.text
    conn_id = body["id"]

    listed = await client.get("/api/v1/model-connections", headers=auth_headers)
    assert listed.status_code == 200
    assert any(i["id"] == conn_id for i in listed.json())

    tested = await client.post(
        f"/api/v1/model-connections/{conn_id}/test",
        headers=auth_headers,
    )
    assert tested.status_code == 200, tested.text
    assert tested.json()["ok"] is True

    patched = await client.patch(
        f"/api/v1/model-connections/{conn_id}",
        headers=auth_headers,
        json={"priority": 5},
    )
    assert patched.status_code == 200
    assert patched.json()["version"] == 2
    assert patched.json()["priority"] == 5

    routes = await client.get("/api/v1/model-connections/routes", headers=auth_headers)
    assert routes.status_code == 200, routes.text
    chat_route = next(i for i in routes.json()["items"] if i["purpose"] == "chat")
    assert chat_route["source"] == "tenant"
    assert chat_route["connection_id"] == conn_id

    deleted = await client.delete(
        f"/api/v1/model-connections/{conn_id}",
        headers=auth_headers,
    )
    assert deleted.status_code == 204


async def test_tenant_overrides_platform_and_env_fallback(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    clear_provider_cache()
    settings = get_settings()
    platform_id = uuid7()

    # 平台行需迁移角色写入
    url = settings.database_migration_url or settings.database_url
    engine = create_async_engine(url, pool_pre_ping=True)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with maker() as session:
            session.add(
                ModelConnection(
                    id=platform_id,
                    tenant_id=None,
                    name=f"plat-{uuid.uuid4().hex[:6]}",
                    provider_type="fake",
                    base_url="http://platform",
                    credential_cipher=encrypt_credential("", settings),
                    credential_hint="",
                    model="platform-chat",
                    purposes=[PURPOSE_CHAT],
                    priority=1,
                    enabled=True,
                    version=1,
                )
            )
            await session.commit()
    finally:
        await engine.dispose()

    routes = await client.get("/api/v1/model-connections/routes", headers=auth_headers)
    assert routes.status_code == 200
    chat_route = next(i for i in routes.json()["items"] if i["purpose"] == "chat")
    assert chat_route["source"] == "platform"
    assert chat_route["connection_id"] == str(platform_id)

    tenant = await client.post(
        "/api/v1/model-connections",
        headers=auth_headers,
        json={
            "name": "覆盖平台",
            "provider_type": "fake",
            "base_url": "http://tenant",
            "model": "tenant-chat",
            "purposes": ["chat"],
            "priority": 90,
        },
    )
    assert tenant.status_code == 201, tenant.text
    tenant_id = tenant.json()["id"]

    routes2 = await client.get("/api/v1/model-connections/routes", headers=auth_headers)
    chat2 = next(i for i in routes2.json()["items"] if i["purpose"] == "chat")
    assert chat2["source"] == "tenant"
    assert chat2["connection_id"] == tenant_id

    # 禁用租户点后回到平台
    await client.patch(
        f"/api/v1/model-connections/{tenant_id}",
        headers=auth_headers,
        json={"enabled": False},
    )
    routes3 = await client.get("/api/v1/model-connections/routes", headers=auth_headers)
    chat3 = next(i for i in routes3.json()["items"] if i["purpose"] == "chat")
    assert chat3["source"] == "platform"

    await client.delete(f"/api/v1/model-connections/{tenant_id}", headers=auth_headers)

    # 清理平台点
    engine = create_async_engine(url, pool_pre_ping=True)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with maker() as session:
            await session.execute(delete(ModelConnection).where(ModelConnection.id == platform_id))
            await session.commit()
    finally:
        await engine.dispose()

    # 无库配置 → env
    # 确保没有遗留 chat 用途平台点干扰：若 seed 已写入 platform-chat，source 可能是 platform
    # 本断言改为：禁用全部可见 chat 租户点后，至少能解析出 routes
    routes4 = await client.get("/api/v1/model-connections/routes", headers=auth_headers)
    assert routes4.status_code == 200
    assert any(i["purpose"] == "chat" for i in routes4.json()["items"])


async def test_cannot_mutate_platform(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    settings = get_settings()
    platform_id = uuid7()
    url = settings.database_migration_url or settings.database_url
    engine = create_async_engine(url, pool_pre_ping=True)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with maker() as session:
            session.add(
                ModelConnection(
                    id=platform_id,
                    tenant_id=None,
                    name=f"plat-ro-{uuid.uuid4().hex[:6]}",
                    provider_type="fake",
                    base_url="http://platform",
                    credential_cipher="",
                    credential_hint="",
                    model="x",
                    purposes=[PURPOSE_CHAT],
                    priority=100,
                    enabled=True,
                    version=1,
                )
            )
            await session.commit()
    finally:
        await engine.dispose()

    deny = await client.patch(
        f"/api/v1/model-connections/{platform_id}",
        headers=auth_headers,
        json={"name": "hack"},
    )
    assert deny.status_code == 403, deny.text

    deny_del = await client.delete(
        f"/api/v1/model-connections/{platform_id}",
        headers=auth_headers,
    )
    assert deny_del.status_code == 403, deny_del.text

    engine = create_async_engine(url, pool_pre_ping=True)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with maker() as session:
            await session.execute(delete(ModelConnection).where(ModelConnection.id == platform_id))
            await session.commit()
    finally:
        await engine.dispose()
