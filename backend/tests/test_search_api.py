"""POST /search 集成测试。"""

from __future__ import annotations

import uuid

from httpx import AsyncClient
from sqlalchemy import func, select

from app.modules.ingestion.chunkers.tsv import build_tsv
from app.modules.knowledge.models import Chunk, Document, KnowledgeBase
from app.platform.db import session_scope
from app.platform.ids import uuid7
from app.platform.llm.fake import FakeEmbeddingProvider
from tests.conftest import Fixture


async def test_search_returns_rrf_scores(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    emb = FakeEmbeddingProvider(dimension=1024)
    texts = [
        "液压泵 HYD-2201 的保养周期为三个月一次。",
        "电气柜接地电阻不得超过 4 欧姆。",
    ]
    vectors = await emb.embed(texts, input_type="document")

    async with session_scope(
        tenant_id=fixture_data.primary_tenant_id, user_id=fixture_data.user_id
    ) as session:
        kb = KnowledgeBase(
            tenant_id=fixture_data.primary_tenant_id,
            name="检索测试库",
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
            storage_key=f"tenants/{fixture_data.primary_tenant_id}/documents/{uuid7()}/original.txt",
            status="ready",
            page_count=1,
            uploaded_by=fixture_data.user_id,
        )
        session.add(doc)
        await session.flush()
        for i, (content, vec) in enumerate(zip(texts, vectors, strict=True)):
            tsv_text = build_tsv(content)
            tsv_value = (
                await session.execute(select(func.to_tsvector("simple", tsv_text)))
            ).scalar_one()
            session.add(
                Chunk(
                    tenant_id=fixture_data.primary_tenant_id,
                    kb_id=kb.id,
                    document_id=doc.id,
                    seq=i,
                    content=content,
                    raw_content=content,
                    heading_path=["保养"],
                    chunk_type="text",
                    page_start=1,
                    page_end=1,
                    bboxes=[],
                    token_count=20,
                    embedding=vec,
                    tsv=tsv_value,
                )
            )
        kb_id = kb.id

    resp = await client.post(
        "/api/v1/search",
        headers=auth_headers,
        json={"query": "HYD-2201 保养周期", "kb_ids": [str(kb_id)], "top_k": 5},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["results"], "应至少命中一条"
    assert "rrf" in body["results"][0]["scores"]
    assert "vector_ms" in body["stats"]


async def test_search_applies_profile_synonyms(
    client: AsyncClient, auth_headers: dict[str, str], fixture_data: Fixture
) -> None:
    from tests.test_profile_crud import _ensure_builtin_general

    await _ensure_builtin_general()
    code = f"syn_{uuid.uuid4().hex[:8]}"
    derived = await client.post(
        "/api/v1/industry-profiles",
        headers=auth_headers,
        json={
            "base_code": "general",
            "code": code,
            "parse_rules": {"dictionary": [], "synonyms": {"泵浦": "液压泵"}},
        },
    )
    assert derived.status_code == 201, derived.text

    kb_resp = await client.post(
        "/api/v1/knowledge-bases",
        headers=auth_headers,
        json={"name": "同义词库", "profile_code": code},
    )
    assert kb_resp.status_code == 201, kb_resp.text
    kb_id = kb_resp.json()["id"]

    emb = FakeEmbeddingProvider(dimension=1024)
    content = "液压泵 HYD-2201 的保养周期为三个月一次。"
    vec = (await emb.embed([content], input_type="document"))[0]
    async with session_scope(
        tenant_id=fixture_data.primary_tenant_id, user_id=fixture_data.user_id
    ) as session:
        doc = Document(
            tenant_id=fixture_data.primary_tenant_id,
            kb_id=uuid.UUID(kb_id),
            title="设备手册",
            source_type="upload",
            mime_type="text/plain",
            file_size=80,
            checksum=f"sha256:{uuid.uuid4().hex}",
            storage_key=f"tenants/{fixture_data.primary_tenant_id}/documents/{uuid7()}/s.txt",
            status="ready",
            page_count=1,
            uploaded_by=fixture_data.user_id,
        )
        session.add(doc)
        await session.flush()
        tsv_value = (
            await session.execute(select(func.to_tsvector("simple", build_tsv(content))))
        ).scalar_one()
        session.add(
            Chunk(
                tenant_id=fixture_data.primary_tenant_id,
                kb_id=uuid.UUID(kb_id),
                document_id=doc.id,
                seq=0,
                content=content,
                raw_content=content,
                heading_path=[],
                chunk_type="text",
                page_start=1,
                page_end=1,
                bboxes=[],
                token_count=12,
                embedding=vec,
                tsv=tsv_value,
            )
        )

    resp = await client.post(
        "/api/v1/search",
        headers=auth_headers,
        json={"query": "泵浦保养周期", "kb_ids": [kb_id], "top_k": 5},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "液压泵" in body["query"]
    assert body["results"]
