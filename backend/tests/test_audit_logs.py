"""M4：审计日志写入与查询验收。"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import delete

from app.modules.audit.models import AuditLog
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


async def test_login_writes_audit(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    # auth_headers fixture 已登录一次；再显式登录并按 action 过滤
    await _login(
        client, fixture_data.email, fixture_data.password, fixture_data.primary_tenant_slug
    )
    resp = await client.get(
        "/api/v1/admin/audit-logs",
        headers=auth_headers,
        params={"action": "auth.login"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    assert all(i["action"] == "auth.login" for i in body["items"])


async def test_member_cannot_read_audit(
    client: AsyncClient, fixture_data: Fixture
) -> None:
    member_email = f"aud-m-{uuid.uuid4().hex[:8]}@example.com"
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

    headers = await _login(
        client, member_email, TEST_PASSWORD, fixture_data.primary_tenant_slug
    )
    resp = await client.get("/api/v1/admin/audit-logs", headers=headers)
    assert resp.status_code == 403, resp.text

    async with session_scope(tenant_id=fixture_data.primary_tenant_id) as session:
        await session.execute(delete(Membership).where(Membership.user_id == member_id))
    async with session_scope() as session:
        await session.execute(delete(User).where(User.id == member_id))


async def test_membership_and_grant_audit_hooks(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    orphan_email = f"aud-o-{uuid.uuid4().hex[:8]}@example.com"
    async with session_scope() as session:
        user = User(
            email=orphan_email,
            display_name="审计对象",
            password_hash=hash_password(TEST_PASSWORD),
        )
        session.add(user)
        await session.flush()
        orphan_id = user.id

    add = await client.post(
        "/api/v1/memberships",
        headers=auth_headers,
        json={"email": orphan_email, "role": "member"},
    )
    assert add.status_code == 201, add.text

    patch = await client.patch(
        f"/api/v1/memberships/{orphan_id}",
        headers=auth_headers,
        json={"role": "admin"},
    )
    assert patch.status_code == 200, patch.text

    remove = await client.delete(
        f"/api/v1/memberships/{orphan_id}",
        headers=auth_headers,
    )
    assert remove.status_code == 204, remove.text

    kb = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "审计库", "visibility": "private"},
    )
    assert kb.status_code == 201, kb.text
    kb_id = kb.json()["id"]

    grant = await client.put(
        f"/api/v1/knowledge-bases/{kb_id}/grants/{orphan_id}",
        headers=auth_headers,
        json={"permission": "read"},
    )
    assert grant.status_code == 200, grant.text

    grant2 = await client.put(
        f"/api/v1/knowledge-bases/{kb_id}/grants/{orphan_id}",
        headers=auth_headers,
        json={"permission": "write"},
    )
    assert grant2.status_code == 200, grant2.text

    revoke = await client.delete(
        f"/api/v1/knowledge-bases/{kb_id}/grants/{orphan_id}",
        headers=auth_headers,
    )
    assert revoke.status_code == 204, revoke.text

    deleted = await client.delete(
        f"/api/v1/knowledge-bases/{kb_id}",
        headers=auth_headers,
    )
    assert deleted.status_code == 204, deleted.text

    switch = await client.post(
        "/api/v1/auth/switch-tenant",
        headers=auth_headers,
        json={"tenant_id": str(fixture_data.secondary_tenant_id)},
    )
    assert switch.status_code == 200, switch.text
    # 切回 primary 查审计（secondary 是 member，读 admin 接口会 403）
    back = await client.post(
        "/api/v1/auth/switch-tenant",
        headers={"Authorization": f"Bearer {switch.json()['access_token']}"},
        json={"tenant_id": str(fixture_data.primary_tenant_id)},
    )
    assert back.status_code == 200, back.text
    owner_headers = {"Authorization": f"Bearer {back.json()['access_token']}"}

    expected_actions = {
        "membership.add",
        "membership.role_change",
        "membership.remove",
        "kb_grant.create",
        "kb_grant.update",
        "kb_grant.delete",
        "knowledge_base.delete",
        "auth.switch_tenant",
    }
    resp = await client.get(
        "/api/v1/admin/audit-logs",
        headers=owner_headers,
        params={"limit": 200},
    )
    assert resp.status_code == 200, resp.text
    found = {item["action"] for item in resp.json()["items"]}
    missing = expected_actions - found
    assert not missing, f"missing audit actions: {missing}"

    async with session_scope() as session:
        await session.execute(delete(User).where(User.id == orphan_id))

    # 清理本租户测试产生的审计，避免污染（可选）
    async with session_scope(
        tenant_id=fixture_data.primary_tenant_id, user_id=fixture_data.user_id
    ) as session:
        await session.execute(
            delete(AuditLog).where(AuditLog.tenant_id == fixture_data.primary_tenant_id)
        )
