"""documents.enabled：禁用文档的 chunk 不得出现在检索结果中；PATCH 启停与列表字段。"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from app.modules.ingestion.chunkers.tsv import build_tsv
from app.modules.knowledge.models import Chunk, Document, KnowledgeBase
from app.modules.retrieval.repository import RetrievalRepository
from app.platform.db import session_scope
from app.platform.ids import uuid7
from app.platform.llm.fake import FakeEmbeddingProvider
from tests.conftest import Fixture
from tests.test_profile_crud import _ensure_builtin_general


async def _seed_ready_doc_for_search(
    fixture_data: Fixture,
    *,
    content: str = "液压泵 HYD-2201 的保养周期为三个月一次。",
) -> tuple[uuid.UUID, uuid.UUID]:
    emb = FakeEmbeddingProvider(dimension=1024)
    vec = (await emb.embed([content], input_type="document"))[0]
    async with session_scope(
        tenant_id=fixture_data.primary_tenant_id, user_id=fixture_data.user_id
    ) as session:
        kb = KnowledgeBase(
            tenant_id=fixture_data.primary_tenant_id,
            name="PATCH 启用检索库",
            embedding_model="fake",
            embedding_dim=1024,
            created_by=fixture_data.user_id,
        )
        session.add(kb)
        await session.flush()
        doc = Document(
            tenant_id=fixture_data.primary_tenant_id,
            kb_id=kb.id,
            title="设备手册",
            source_type="upload",
            mime_type="text/plain",
            file_size=100,
            checksum=f"sha256:{uuid.uuid4().hex}",
            storage_key=f"tenants/{fixture_data.primary_tenant_id}/documents/{uuid7()}/m.txt",
            status="ready",
            page_count=1,
            uploaded_by=fixture_data.user_id,
            enabled=True,
        )
        session.add(doc)
        await session.flush()
        tsv_value = (
            await session.execute(select(func.to_tsvector("simple", build_tsv(content))))
        ).scalar_one()
        session.add(
            Chunk(
                tenant_id=fixture_data.primary_tenant_id,
                kb_id=kb.id,
                document_id=doc.id,
                seq=0,
                content=content,
                raw_content=content,
                heading_path=[],
                chunk_type="text",
                page_start=1,
                page_end=1,
                bboxes=[],
                token_count=20,
                embedding=vec,
                tsv=tsv_value,
            )
        )
        return kb.id, doc.id


async def test_vector_search_excludes_disabled_document_chunks(
    fixture_data: Fixture,
) -> None:
    emb = FakeEmbeddingProvider(dimension=1024)
    enabled_text = "液压泵 HYD-2201 的保养周期为三个月一次。"
    disabled_text = "电气柜接地电阻不得超过 4 欧姆。"
    vectors = await emb.embed([enabled_text, disabled_text], input_type="document")
    query_vec = (await emb.embed(["HYD-2201 保养"], input_type="query"))[0]

    async with session_scope(
        tenant_id=fixture_data.primary_tenant_id, user_id=fixture_data.user_id
    ) as session:
        kb = KnowledgeBase(
            tenant_id=fixture_data.primary_tenant_id,
            name="enabled 过滤测试库",
            embedding_model="fake",
            embedding_dim=1024,
            created_by=fixture_data.user_id,
        )
        session.add(kb)
        await session.flush()

        enabled_doc = Document(
            tenant_id=fixture_data.primary_tenant_id,
            kb_id=kb.id,
            title="启用文档",
            source_type="upload",
            mime_type="text/plain",
            file_size=100,
            checksum=f"sha256:{uuid.uuid4().hex}",
            storage_key=f"tenants/{fixture_data.primary_tenant_id}/documents/{uuid7()}/on.txt",
            status="ready",
            page_count=1,
            uploaded_by=fixture_data.user_id,
            enabled=True,
        )
        disabled_doc = Document(
            tenant_id=fixture_data.primary_tenant_id,
            kb_id=kb.id,
            title="禁用文档",
            source_type="upload",
            mime_type="text/plain",
            file_size=100,
            checksum=f"sha256:{uuid.uuid4().hex}",
            storage_key=f"tenants/{fixture_data.primary_tenant_id}/documents/{uuid7()}/off.txt",
            status="ready",
            page_count=1,
            uploaded_by=fixture_data.user_id,
            enabled=False,
        )
        session.add_all([enabled_doc, disabled_doc])
        await session.flush()

        chunks_by_flag: dict[str, uuid.UUID] = {}
        for flag, doc, content, vec in (
            ("enabled", enabled_doc, enabled_text, vectors[0]),
            ("disabled", disabled_doc, disabled_text, vectors[1]),
        ):
            tsv_value = (
                await session.execute(select(func.to_tsvector("simple", build_tsv(content))))
            ).scalar_one()
            chunk = Chunk(
                tenant_id=fixture_data.primary_tenant_id,
                kb_id=kb.id,
                document_id=doc.id,
                seq=0,
                content=content,
                raw_content=content,
                heading_path=[],
                chunk_type="text",
                page_start=1,
                page_end=1,
                bboxes=[],
                token_count=20,
                embedding=vec,
                tsv=tsv_value,
            )
            session.add(chunk)
            await session.flush()
            chunks_by_flag[flag] = chunk.id

        repo = RetrievalRepository(session)
        hits = await repo.vector_search(
            tenant_id=fixture_data.primary_tenant_id,
            kb_ids=[kb.id],
            query_vec=query_vec,
            limit=10,
        )
        hit_ids = {h.chunk_id for h in hits}
        assert chunks_by_flag["enabled"] in hit_ids
        assert chunks_by_flag["disabled"] not in hit_ids

        # jieba 分词后 tsv 为独立 token；plainto_tsquery 需用已切出的词
        ft_hits = await repo.fulltext_search(
            tenant_id=fixture_data.primary_tenant_id,
            kb_ids=[kb.id],
            tsv_query="保养",
            limit=10,
        )
        ft_ids = {h.chunk_id for h in ft_hits}
        assert chunks_by_flag["enabled"] in ft_ids
        assert chunks_by_flag["disabled"] not in ft_ids

        ft_disabled_query = await repo.fulltext_search(
            tenant_id=fixture_data.primary_tenant_id,
            kb_ids=[kb.id],
            tsv_query="电气柜",
            limit=10,
        )
        assert chunks_by_flag["disabled"] not in {h.chunk_id for h in ft_disabled_query}


async def test_patch_enabled_excludes_then_includes_in_search(
    client: AsyncClient,
    auth_headers: dict[str, str],
    fixture_data: Fixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # 共享库若有平台 embedding 接入点，会绕过 IRP_EMBEDDING_PROVIDER=fake 打网失败
    async def _fake_embedding(self: object, tenant_id: uuid.UUID, *, cache: bool = True) -> object:
        return FakeEmbeddingProvider(dimension=1024)

    monkeypatch.setattr(
        "app.modules.modelops.provider_factory.ProviderFactory.get_embedding",
        _fake_embedding,
    )

    kb_id, doc_id = await _seed_ready_doc_for_search(fixture_data)
    query = {"query": "HYD-2201 保养", "kb_ids": [str(kb_id)], "top_k": 5}

    hit = await client.post("/api/v1/search", headers=auth_headers, json=query)
    assert hit.status_code == 200, hit.text
    assert any(r["document_id"] == str(doc_id) for r in hit.json()["results"])

    off = await client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=auth_headers,
        json={"enabled": False},
    )
    assert off.status_code == 200, off.text
    assert off.json()["enabled"] is False
    assert "chunk_count" in off.json()
    assert "metadata" in off.json()

    miss = await client.post("/api/v1/search", headers=auth_headers, json=query)
    assert miss.status_code == 200, miss.text
    assert all(r["document_id"] != str(doc_id) for r in miss.json()["results"])

    on = await client.patch(
        f"/api/v1/documents/{doc_id}",
        headers=auth_headers,
        json={"enabled": True},
    )
    assert on.status_code == 200, on.text
    assert on.json()["enabled"] is True

    again = await client.post("/api/v1/search", headers=auth_headers, json=query)
    assert again.status_code == 200, again.text
    assert any(r["document_id"] == str(doc_id) for r in again.json()["results"])


async def test_patch_metadata_unknown_key_422(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    await _ensure_builtin_general()
    code = f"patch_meta_{uuid.uuid4().hex[:8]}"
    derived = await client.post(
        "/api/v1/industry-profiles",
        headers=auth_headers,
        json={
            "base_code": "general",
            "code": code,
            "name": "PATCH 元数据 schema",
            "metadata_schema": {
                "equipment_model": {"type": "string", "required": False},
            },
        },
    )
    assert derived.status_code == 201, derived.text

    kb = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "PATCH 元数据库", "profile_code": code},
    )
    assert kb.status_code == 201, kb.text
    kb_id = kb.json()["id"]

    document_id = uuid7()
    reg = await client.post(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
        json={
            "document_id": str(document_id),
            "storage_key": (
                f"tenants/{fixture_data.primary_tenant_id}/documents/{document_id}/a.pdf"
            ),
            "title": "样例",
            "checksum": "sha256:" + "b" * 64,
            "file_size": 10,
            "mime_type": "application/pdf",
            "metadata": {},
        },
    )
    assert reg.status_code == 202, reg.text

    bad = await client.patch(
        f"/api/v1/documents/{document_id}",
        headers=auth_headers,
        json={"metadata": {"unknown_field": "x"}},
    )
    assert bad.status_code == 422, bad.text
    assert bad.json()["error"]["code"] == "metadata_invalid"


async def test_list_documents_includes_chunk_count(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    kb_id, _doc_id = await _seed_ready_doc_for_search(fixture_data)
    listed = await client.get(
        f"/api/v1/knowledge-bases/{kb_id}/documents",
        headers=auth_headers,
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()
    assert len(rows) == 1
    assert rows[0]["chunk_count"] == 1
    assert rows[0]["enabled"] is True
    assert isinstance(rows[0]["metadata"], dict)
