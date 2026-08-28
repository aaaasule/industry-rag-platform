"""documents.enabled：禁用文档的 chunk 不得出现在检索结果中。"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.modules.ingestion.chunkers.tsv import build_tsv
from app.modules.knowledge.models import Chunk, Document, KnowledgeBase
from app.modules.retrieval.repository import RetrievalRepository
from app.platform.db import session_scope
from app.platform.ids import uuid7
from app.platform.llm.fake import FakeEmbeddingProvider
from tests.conftest import Fixture


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
