"""测试夹具。

集成测试打真实 Postgres，不打桩：RLS 策略、约束、citext 这些正是最容易出错
且 SQLite 无法覆盖的地方，用内存库测等于没测。
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.main import create_app
from app.modules.chat.models import Citation, Conversation, Message, MessageFeedback
from app.modules.identity.models import ROLE_MEMBER, ROLE_OWNER, Membership, Tenant, User
from app.platform.config import get_settings
from app.platform.db import session_scope
from app.platform.security import hash_password

TEST_PASSWORD = "Test-Passw0rd!"


@pytest.fixture(scope="session", autouse=True)
def _force_fake_providers_for_tests() -> None:
    """本地 .env 可能切到真实模型；单测/集成测必须保持 Fake，避免外网与密钥依赖。"""
    import os

    os.environ["IRP_LLM_PROVIDER"] = "fake"
    os.environ["IRP_EMBEDDING_PROVIDER"] = "fake"
    os.environ["IRP_RERANK_PROVIDER"] = "fake"
    os.environ["IRP_RETRIEVAL_RERANK_DEFAULT"] = "false"
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    # 走 lifespan 才能拿到引擎与 Provider，和线上启动路径保持一致
    async with (
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http,
        app.router.lifespan_context(app),
    ):
        yield http


@dataclass(frozen=True, slots=True)
class Fixture:
    """一个用户 + 两个租户，覆盖"跨租户切换"这一核心场景。"""

    user_id: uuid.UUID
    email: str
    password: str
    primary_tenant_id: uuid.UUID
    primary_tenant_slug: str
    secondary_tenant_id: uuid.UUID
    secondary_tenant_slug: str
    outsider_tenant_id: uuid.UUID


@pytest.fixture
async def fixture_data() -> AsyncIterator[Fixture]:
    marker = uuid.uuid4().hex[:8]
    email = f"tester-{marker}@example.com"

    async with session_scope() as session:
        primary = Tenant(slug=f"primary-{marker}", name="主租户")
        secondary = Tenant(slug=f"secondary-{marker}", name="次租户")
        outsider = Tenant(slug=f"outsider-{marker}", name="无关租户")
        user = User(email=email, display_name="测试员", password_hash=hash_password(TEST_PASSWORD))
        session.add_all([primary, secondary, outsider, user])
        await session.flush()
        ids = (primary.id, secondary.id, outsider.id, user.id)

    for tenant_id, role in ((ids[0], ROLE_OWNER), (ids[1], ROLE_MEMBER)):
        async with session_scope(tenant_id=tenant_id) as session:
            session.add(Membership(tenant_id=tenant_id, user_id=ids[3], role=role))

    yield Fixture(
        user_id=ids[3],
        email=email,
        password=TEST_PASSWORD,
        primary_tenant_id=ids[0],
        primary_tenant_slug=f"primary-{marker}",
        secondary_tenant_id=ids[1],
        secondary_tenant_slug=f"secondary-{marker}",
        outsider_tenant_id=ids[2],
    )

    async with session_scope(tenant_id=ids[0], user_id=ids[3]) as session:
        # chat 表有 RLS；必须在租户上下文中清理
        conv_ids = (
            (await session.execute(select(Conversation.id).where(Conversation.user_id == ids[3])))
            .scalars()
            .all()
        )
        if conv_ids:
            msg_ids = (
                (
                    await session.execute(
                        select(Message.id).where(Message.conversation_id.in_(conv_ids))
                    )
                )
                .scalars()
                .all()
            )
            if msg_ids:
                await session.execute(
                    delete(MessageFeedback).where(MessageFeedback.message_id.in_(msg_ids))
                )
                await session.execute(delete(Citation).where(Citation.message_id.in_(msg_ids)))
                await session.execute(delete(Message).where(Message.id.in_(msg_ids)))
            await session.execute(delete(Conversation).where(Conversation.id.in_(conv_ids)))

    async with session_scope() as session:
        # memberships 由 tenants 的级联删除带走
        await session.execute(delete(Tenant).where(Tenant.id.in_(ids[:3])))
        await session.execute(delete(User).where(User.id == ids[3]))


@pytest.fixture
async def auth_headers(client: AsyncClient, fixture_data: Fixture) -> dict[str, str]:
    resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": fixture_data.email,
            "password": fixture_data.password,
            "tenant_slug": fixture_data.primary_tenant_slug,
        },
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(autouse=True, scope="session")
def _assert_local_environment() -> None:
    """防止误对预发/生产库执行测试——测试会删数据。"""
    assert get_settings().is_local, "测试只能在 local 环境运行"
