"""KnowledgeBaseOut.my_permission 与 visible_kb_ids 对齐。"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import delete

from app.modules.identity.models import ROLE_MEMBER, Membership, User
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


async def _create_member(fixture_data: Fixture) -> tuple[uuid.UUID, str]:
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
    return member_id, member_email


async def _cleanup_member(member_id: uuid.UUID, fixture_data: Fixture) -> None:
    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        await session.execute(delete(Membership).where(Membership.user_id == member_id))
    async with session_scope() as session:
        await session.execute(delete(User).where(User.id == member_id))


async def test_owner_my_permission_manage(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    create = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "owner 库", "visibility": "private"},
    )
    assert create.status_code == 201, create.text
    assert create.json()["my_permission"] == "manage"

    got = await client.get(f"/api/v1/knowledge-bases/{create.json()['id']}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["my_permission"] == "manage"


async def test_member_grant_write_my_permission(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    create = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "授权写库", "visibility": "private"},
    )
    assert create.status_code == 201, create.text
    kb_id = create.json()["id"]

    member_id, member_email = await _create_member(fixture_data)
    try:
        grant = await client.put(
            f"/api/v1/knowledge-bases/{kb_id}/grants/{member_id}",
            headers=auth_headers,
            json={"permission": "write"},
        )
        assert grant.status_code == 200, grant.text

        member_headers = await _login(
            client, member_email, TEST_PASSWORD, fixture_data.primary_tenant_slug
        )
        got = await client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=member_headers)
        assert got.status_code == 200
        assert got.json()["my_permission"] == "write"
    finally:
        await _cleanup_member(member_id, fixture_data)


async def test_member_tenant_visible_my_permission_read(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    create = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "租户可见库", "visibility": "tenant"},
    )
    assert create.status_code == 201, create.text
    kb_id = create.json()["id"]

    member_id, member_email = await _create_member(fixture_data)
    try:
        member_headers = await _login(
            client, member_email, TEST_PASSWORD, fixture_data.primary_tenant_slug
        )
        got = await client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=member_headers)
        assert got.status_code == 200
        assert got.json()["my_permission"] == "read"
    finally:
        await _cleanup_member(member_id, fixture_data)
