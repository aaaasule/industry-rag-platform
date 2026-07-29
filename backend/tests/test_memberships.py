"""M4：租户成员管理验收。"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import delete

from app.modules.identity.models import ROLE_ADMIN, ROLE_MEMBER, Membership, User
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


async def _create_user_in_tenant(
    *,
    tenant_id: uuid.UUID,
    email: str,
    role: str,
    display_name: str = "临时用户",
) -> uuid.UUID:
    async with session_scope(tenant_id=tenant_id) as session:
        user = User(
            email=email,
            display_name=display_name,
            password_hash=hash_password(TEST_PASSWORD),
        )
        session.add(user)
        await session.flush()
        session.add(Membership(tenant_id=tenant_id, user_id=user.id, role=role))
        return user.id


async def _delete_user(user_id: uuid.UUID, tenant_id: uuid.UUID) -> None:
    async with session_scope(tenant_id=tenant_id) as session:
        await session.execute(delete(Membership).where(Membership.user_id == user_id))
    async with session_scope() as session:
        await session.execute(delete(User).where(User.id == user_id))


async def test_member_cannot_list_memberships(
    client: AsyncClient, fixture_data: Fixture
) -> None:
    member_email = f"mem-{uuid.uuid4().hex[:8]}@example.com"
    member_id = await _create_user_in_tenant(
        tenant_id=fixture_data.primary_tenant_id,
        email=member_email,
        role=ROLE_MEMBER,
    )
    headers = await _login(
        client, member_email, TEST_PASSWORD, fixture_data.primary_tenant_slug
    )
    resp = await client.get("/api/v1/memberships", headers=headers)
    assert resp.status_code == 403, resp.text
    await _delete_user(member_id, fixture_data.primary_tenant_id)


async def test_owner_lists_and_adds_member(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    listed = await client.get("/api/v1/memberships", headers=auth_headers)
    assert listed.status_code == 200, listed.text
    assert any(i["user_id"] == str(fixture_data.user_id) for i in listed.json()["items"])

    orphan_email = f"orphan-{uuid.uuid4().hex[:8]}@example.com"
    async with session_scope() as session:
        user = User(
            email=orphan_email,
            display_name="待加入",
            password_hash=hash_password(TEST_PASSWORD),
        )
        session.add(user)
        await session.flush()
        orphan_id = user.id

    created = await client.post(
        "/api/v1/memberships",
        headers=auth_headers,
        json={"email": orphan_email, "role": "member"},
    )
    assert created.status_code == 201, created.text
    assert created.json()["email"] == orphan_email
    assert created.json()["role"] == "member"

    again = await client.post(
        "/api/v1/memberships",
        headers=auth_headers,
        json={"email": orphan_email, "role": "member"},
    )
    assert again.status_code == 409, again.text

    unknown = await client.post(
        "/api/v1/memberships",
        headers=auth_headers,
        json={"email": f"nope-{uuid.uuid4().hex[:8]}@example.com", "role": "member"},
    )
    assert unknown.status_code == 404, unknown.text

    await _delete_user(orphan_id, fixture_data.primary_tenant_id)


async def test_cannot_demote_last_owner(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    resp = await client.patch(
        f"/api/v1/memberships/{fixture_data.user_id}",
        headers=auth_headers,
        json={"role": "admin"},
    )
    assert resp.status_code == 400, resp.text
    assert "last owner" in resp.json()["error"]["message"]


async def test_admin_cannot_touch_owner(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    admin_email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
    admin_id = await _create_user_in_tenant(
        tenant_id=fixture_data.primary_tenant_id,
        email=admin_email,
        role=ROLE_ADMIN,
        display_name="管理员",
    )
    # 再加一个 member，供 admin 尝试删除 owner 以外的操作对照
    member_email = f"m2-{uuid.uuid4().hex[:8]}@example.com"
    member_id = await _create_user_in_tenant(
        tenant_id=fixture_data.primary_tenant_id,
        email=member_email,
        role=ROLE_MEMBER,
    )

    admin_headers = await _login(
        client, admin_email, TEST_PASSWORD, fixture_data.primary_tenant_slug
    )

    deny_role = await client.patch(
        f"/api/v1/memberships/{fixture_data.user_id}",
        headers=admin_headers,
        json={"role": "admin"},
    )
    assert deny_role.status_code == 403, deny_role.text

    deny_del = await client.delete(
        f"/api/v1/memberships/{fixture_data.user_id}",
        headers=admin_headers,
    )
    assert deny_del.status_code == 403, deny_del.text

    ok_del = await client.delete(
        f"/api/v1/memberships/{member_id}",
        headers=admin_headers,
    )
    assert ok_del.status_code == 204, ok_del.text

    await _delete_user(admin_id, fixture_data.primary_tenant_id)
    async with session_scope() as session:
        await session.execute(delete(User).where(User.id == member_id))


async def test_cannot_remove_self(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    # 需要第二个 owner 才不会撞到 last-owner；但自删应优先报 cannot remove yourself
    other_email = f"own2-{uuid.uuid4().hex[:8]}@example.com"
    other_id = await _create_user_in_tenant(
        tenant_id=fixture_data.primary_tenant_id,
        email=other_email,
        role="owner",
    )
    resp = await client.delete(
        f"/api/v1/memberships/{fixture_data.user_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 400, resp.text
    assert "yourself" in resp.json()["error"]["message"]
    await _delete_user(other_id, fixture_data.primary_tenant_id)
