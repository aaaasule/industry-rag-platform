"""M4：kb_grants 与跨租户可见性验收。"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import delete

from app.modules.identity.models import ROLE_MEMBER, Membership, User
from app.modules.knowledge.models import KnowledgeBase
from app.platform.db import session_scope
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


async def test_private_kb_hidden_without_grant(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    """owner 建 private KB；同租户 member 无 grant → list 不见、get 403。"""
    create = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "私有库", "visibility": "private"},
    )
    assert create.status_code == 201, create.text
    kb_id = create.json()["id"]

    member_email = f"member-{uuid.uuid4().hex[:8]}@example.com"
    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        user = User(
            email=member_email,
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
        member_id = user.id

    member_headers = await _login(
        client, member_email, TEST_PASSWORD, fixture_data.primary_tenant_slug
    )

    listed = await client.get("/api/v1/knowledge-bases", headers=member_headers)
    assert listed.status_code == 200
    assert all(item["id"] != kb_id for item in listed.json())

    denied = await client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=member_headers)
    assert denied.status_code == 403, denied.text

    # owner 授 read 后可见
    grant = await client.put(
        f"/api/v1/knowledge-bases/{kb_id}/grants/{member_id}",
        headers=auth_headers,
        json={"permission": "read"},
    )
    assert grant.status_code == 200, grant.text

    ok = await client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=member_headers)
    assert ok.status_code == 200
    assert ok.json()["id"] == kb_id

    # 撤权后再 403
    revoke = await client.delete(
        f"/api/v1/knowledge-bases/{kb_id}/grants/{member_id}",
        headers=auth_headers,
    )
    assert revoke.status_code == 204
    denied2 = await client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=member_headers)
    assert denied2.status_code == 403

    # 清理临时用户与其可能残留授权
    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        await session.execute(delete(Membership).where(Membership.user_id == member_id))
    async with session_scope() as session:
        await session.execute(delete(User).where(User.id == member_id))


async def test_cross_tenant_kb_404(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    create = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "主租户库", "visibility": "tenant"},
    )
    assert create.status_code == 201
    kb_id = create.json()["id"]

    # 切到 secondary（同用户另一租户）应 404
    switch = await client.post(
        "/api/v1/auth/switch-tenant",
        headers=auth_headers,
        json={"tenant_id": str(fixture_data.secondary_tenant_id)},
    )
    assert switch.status_code == 200, switch.text
    other = {"Authorization": f"Bearer {switch.json()['access_token']}"}

    missing = await client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=other)
    assert missing.status_code == 404, missing.text

    search = await client.post(
        "/api/v1/search",
        headers=other,
        json={"query": "任意", "kb_ids": [kb_id], "top_k": 3},
    )
    assert search.status_code == 404, search.text


async def test_owner_sees_all_without_grant(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    # member 建库后 owner 仍可见（fixture 用户是 owner）
    member_email = f"creator-{uuid.uuid4().hex[:8]}@example.com"
    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        user = User(
            email=member_email,
            display_name="创建者",
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
        member_id = user.id

    member_headers = await _login(
        client, member_email, TEST_PASSWORD, fixture_data.primary_tenant_slug
    )
    create = await client.post(
        "/api/v1/knowledge-bases",
        headers=member_headers,
        json={"name": "成员私有库", "visibility": "private"},
    )
    assert create.status_code == 201, create.text
    kb_id = create.json()["id"]

    owner_get = await client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=auth_headers)
    assert owner_get.status_code == 200

    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        kb = await session.get(KnowledgeBase, uuid.UUID(kb_id))
        if kb is not None:
            await session.delete(kb)
            await session.flush()
        await session.execute(delete(Membership).where(Membership.user_id == member_id))
    async with session_scope() as session:
        await session.execute(delete(User).where(User.id == member_id))
