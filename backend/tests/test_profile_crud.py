"""行业模板派生 / 更新 / KB 改绑。"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.modules.knowledge.models import IndustryProfile
from app.modules.profile.service import resolve_effective_profile
from app.platform.db import session_scope
from app.platform.ids import uuid7
from tests.conftest import Fixture


async def _ensure_builtin_general() -> None:
    async with session_scope() as session:
        exists = (
            await session.execute(
                select(IndustryProfile.id).where(
                    IndustryProfile.code == "general",
                    IndustryProfile.tenant_id.is_(None),
                )
            )
        ).scalar_one_or_none()
        if exists:
            return
        session.add(
            IndustryProfile(
                id=uuid7(),
                tenant_id=None,
                code="general",
                name="通用",
                parse_rules={},
                chunk_rules={
                    "max_tokens": 512,
                    "min_tokens": 80,
                    "overlap_tokens": 64,
                    "clause_mode": False,
                    "keep_heading_prefix": True,
                },
                metadata_schema={},
                prompt_overrides={},
                retrieval_rules={"top_k": 8},
                is_builtin=True,
            )
        )


async def test_derive_patch_and_rebind_kb(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    await _ensure_builtin_general()

    derived = await client.post(
        "/api/v1/industry-profiles",
        headers=auth_headers,
        json={
            "base_code": "general",
            "code": f"custom_{uuid.uuid4().hex[:8]}",
            "name": "自定义通用",
            "retrieval_rules": {"top_k": 12},
        },
    )
    assert derived.status_code == 201, derived.text
    body = derived.json()
    assert body["is_builtin"] is False
    assert body["retrieval_rules"]["top_k"] == 12
    profile_id = body["id"]
    code = body["code"]

    dup = await client.post(
        "/api/v1/industry-profiles",
        headers=auth_headers,
        json={"base_code": "general", "code": code, "name": "重复"},
    )
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "duplicate_profile_code"

    patched = await client.patch(
        f"/api/v1/industry-profiles/{profile_id}",
        headers=auth_headers,
        json={
            "prompt_overrides": {"system": "自定义助手"},
            "retrieval_rules": {"top_k": 15},
        },
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["prompt_overrides"]["system"] == "自定义助手"
    assert patched.json()["retrieval_rules"]["top_k"] == 15

    # 内置不可 PATCH
    listed = await client.get("/api/v1/industry-profiles", headers=auth_headers)
    builtin = next(p for p in listed.json() if p["code"] == "general" and p["is_builtin"])
    bad = await client.patch(
        f"/api/v1/industry-profiles/{builtin['id']}",
        headers=auth_headers,
        json={"name": "篡改"},
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "builtin_immutable"

    kb = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "改绑测试库", "profile_code": "general"},
    )
    assert kb.status_code == 201, kb.text
    kb_id = kb.json()["id"]

    rebound = await client.patch(
        f"/api/v1/knowledge-bases/{kb_id}",
        headers=auth_headers,
        json={"profile_code": code},
    )
    assert rebound.status_code == 200, rebound.text
    assert rebound.json()["profile_id"] == profile_id

    async with session_scope(
        tenant_id=fixture_data.primary_tenant_id, user_id=fixture_data.user_id
    ) as session:
        effective = await resolve_effective_profile(session, uuid.UUID(kb_id))
        assert effective.code == code
        assert effective.retrieval_rules.top_k == 15
        assert effective.prompt_overrides.system == "自定义助手"


async def test_delete_custom_profile(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    await _ensure_builtin_general()

    derived = await client.post(
        "/api/v1/industry-profiles",
        headers=auth_headers,
        json={
            "base_code": "general",
            "code": f"del_{uuid.uuid4().hex[:8]}",
            "name": "待删除模板",
        },
    )
    assert derived.status_code == 201, derived.text
    profile_id = derived.json()["id"]

    deleted = await client.delete(f"/api/v1/industry-profiles/{profile_id}", headers=auth_headers)
    assert deleted.status_code == 204, deleted.text

    listed = await client.get("/api/v1/industry-profiles", headers=auth_headers)
    assert listed.status_code == 200
    assert all(p["id"] != profile_id for p in listed.json())

    again = await client.delete(f"/api/v1/industry-profiles/{profile_id}", headers=auth_headers)
    assert again.status_code == 404


async def test_cannot_delete_builtin(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    await _ensure_builtin_general()

    listed = await client.get("/api/v1/industry-profiles", headers=auth_headers)
    assert listed.status_code == 200
    builtin = next(p for p in listed.json() if p["code"] == "general" and p["is_builtin"])

    resp = await client.delete(f"/api/v1/industry-profiles/{builtin['id']}", headers=auth_headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "builtin_immutable"


async def test_reuse_profile_code_after_soft_delete(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _ensure_builtin_general()
    code = f"reuse_{uuid.uuid4().hex[:8]}"

    derived = await client.post(
        "/api/v1/industry-profiles",
        headers=auth_headers,
        json={"base_code": "general", "code": code, "name": "首次模板"},
    )
    assert derived.status_code == 201, derived.text
    profile_id = derived.json()["id"]

    deleted = await client.delete(f"/api/v1/industry-profiles/{profile_id}", headers=auth_headers)
    assert deleted.status_code == 204, deleted.text

    recreated = await client.post(
        "/api/v1/industry-profiles",
        headers=auth_headers,
        json={"base_code": "general", "code": code, "name": "复用同 code"},
    )
    assert recreated.status_code == 201, recreated.text
    assert recreated.json()["code"] == code
    assert recreated.json()["id"] != profile_id
    assert recreated.json()["name"] == "复用同 code"


async def test_cannot_delete_profile_in_use(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    await _ensure_builtin_general()
    code = f"inuse_{uuid.uuid4().hex[:8]}"

    derived = await client.post(
        "/api/v1/industry-profiles",
        headers=auth_headers,
        json={"base_code": "general", "code": code, "name": "占用中模板"},
    )
    assert derived.status_code == 201, derived.text
    profile_id = derived.json()["id"]

    kb = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "绑定占用库", "profile_code": code},
    )
    assert kb.status_code == 201, kb.text

    resp = await client.delete(f"/api/v1/industry-profiles/{profile_id}", headers=auth_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "profile_in_use"
