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
