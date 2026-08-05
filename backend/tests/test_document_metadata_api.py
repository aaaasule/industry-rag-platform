"""文档登记 metadata 校验 API 集成测试。"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from app.platform.ids import uuid7
from tests.conftest import Fixture
from tests.test_profile_crud import _ensure_builtin_general


async def _setup_kb_with_metadata_schema(
    client: AsyncClient, auth_headers: dict[str, str]
) -> tuple[str, str]:
    await _ensure_builtin_general()
    code = f"meta_{uuid.uuid4().hex[:8]}"
    derived = await client.post(
        "/api/v1/industry-profiles",
        headers=auth_headers,
        json={
            "base_code": "general",
            "code": code,
            "name": "带元数据 schema",
            "metadata_schema": {
                "equipment_model": {"type": "string", "required": True},
            },
        },
    )
    assert derived.status_code == 201, derived.text

    kb = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "元数据校验库", "profile_code": code},
    )
    assert kb.status_code == 201, kb.text
    return kb.json()["id"], code


def _register_payload(
    tenant_id: uuid.UUID, *, metadata: dict | None = None
) -> dict:
    document_id = uuid7()
    return {
        "document_id": str(document_id),
        "storage_key": f"tenants/{tenant_id}/documents/{document_id}/sample.pdf",
        "title": "样例文档",
        "checksum": "sha256:" + "a" * 64,
        "file_size": 1024,
        "mime_type": "application/pdf",
        "metadata": metadata or {},
    }


async def test_register_rejects_unknown_metadata(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    kb_id, _ = await _setup_kb_with_metadata_schema(client, auth_headers)
    resp = await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        json=_register_payload(
            fixture_data.primary_tenant_id,
            metadata={"wrong": 1},
        ),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "metadata_invalid"


async def test_register_rejects_missing_required_metadata(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    kb_id, _ = await _setup_kb_with_metadata_schema(client, auth_headers)
    resp = await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        json=_register_payload(fixture_data.primary_tenant_id, metadata={}),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["code"] == "metadata_invalid"


async def test_register_accepts_valid_metadata(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    kb_id, _ = await _setup_kb_with_metadata_schema(client, auth_headers)
    resp = await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        json=_register_payload(
            fixture_data.primary_tenant_id,
            metadata={"equipment_model": "HYD-2201"},
        ),
    )
    assert resp.status_code == 202, resp.text
    assert resp.json()["document_id"]
