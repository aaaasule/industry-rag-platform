"""知识库文档批量 delete / reingest。"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import select

from app.modules.knowledge.models import Document
from app.platform.db import session_scope
from app.platform.ids import uuid7
from tests.conftest import Fixture


async def _register_doc(
    client: AsyncClient,
    auth_headers: dict[str, str],
    *,
    kb_id: str,
    tenant_id: uuid.UUID,
    title: str,
) -> uuid.UUID:
    document_id = uuid7()
    resp = await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        json={
            "document_id": str(document_id),
            "storage_key": f"tenants/{tenant_id}/documents/{document_id}/batch.pdf",
            "title": title,
            "checksum": "sha256:" + uuid.uuid4().hex + "a" * 32,
            "file_size": 1024,
            "mime_type": "application/pdf",
            "metadata": {},
        },
    )
    assert resp.status_code == 202, resp.text
    return document_id


async def test_batch_delete_soft_deletes_documents(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    kb = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "批量删除库"},
    )
    assert kb.status_code == 201, kb.text
    kb_id = kb.json()["id"]

    doc_a = await _register_doc(
        client,
        auth_headers,
        kb_id=kb_id,
        tenant_id=fixture_data.primary_tenant_id,
        title="批量A",
    )
    doc_b = await _register_doc(
        client,
        auth_headers,
        kb_id=kb_id,
        tenant_id=fixture_data.primary_tenant_id,
        title="批量B",
    )

    resp = await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents/batch",
        headers=auth_headers,
        json={"action": "delete", "document_ids": [str(doc_a), str(doc_b)]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["accepted"] == 2
    assert set(body["job_ids"]) == {str(doc_a), str(doc_b)}

    async with session_scope(
        tenant_id=fixture_data.primary_tenant_id, user_id=fixture_data.user_id
    ) as session:
        rows = (
            (await session.execute(select(Document).where(Document.id.in_([doc_a, doc_b]))))
            .scalars()
            .all()
        )
        assert len(rows) == 2
        assert all(r.deleted_at is not None for r in rows)


async def test_batch_rejects_more_than_50_ids(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    kb = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "批量上限库"},
    )
    assert kb.status_code == 201, kb.text
    kb_id = kb.json()["id"]

    ids = [str(uuid7()) for _ in range(51)]
    resp = await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents/batch",
        headers=auth_headers,
        json={"action": "delete", "document_ids": ids},
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["code"] == "validation_error"


async def test_batch_delete_cross_kb_returns_404_without_side_effects(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    kb_a = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "本库"},
    )
    kb_b = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "他库"},
    )
    assert kb_a.status_code == 201, kb_a.text
    assert kb_b.status_code == 201, kb_b.text
    kb_a_id = kb_a.json()["id"]
    kb_b_id = kb_b.json()["id"]

    local_doc = await _register_doc(
        client,
        auth_headers,
        kb_id=kb_a_id,
        tenant_id=fixture_data.primary_tenant_id,
        title="本库文档",
    )
    foreign_doc = await _register_doc(
        client,
        auth_headers,
        kb_id=kb_b_id,
        tenant_id=fixture_data.primary_tenant_id,
        title="他库文档",
    )

    resp = await client.post(
        f"/api/v1/knowledge-bases/{kb_a_id}/documents/batch",
        headers=auth_headers,
        json={"action": "delete", "document_ids": [str(local_doc), str(foreign_doc)]},
    )
    assert resp.status_code == 404, resp.text

    async with session_scope(
        tenant_id=fixture_data.primary_tenant_id, user_id=fixture_data.user_id
    ) as session:
        local = await session.get(Document, local_doc)
        foreign = await session.get(Document, foreign_doc)
        assert local is not None and local.deleted_at is None
        assert foreign is not None and foreign.deleted_at is None
