"""自适应查询扩展：触发条件、Fake LLM 夹具与 RetrievalService 集成。"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import func, select

from app.modules.identity.models import ROLE_OWNER
from app.modules.ingestion.chunkers.tsv import build_tsv
from app.modules.ingestion.parsers.normalize import normalize
from app.modules.knowledge.models import Chunk, Document, KnowledgeBase
from app.modules.retrieval.base import RankedHit, SearchOptions
from app.modules.retrieval.query_expand import EXPAND_RRF_FLOOR, expand_query, should_expand
from app.modules.retrieval.service import RetrievalService
from app.platform.db import session_scope
from app.platform.ids import uuid7
from app.platform.llm.base import Message
from app.platform.llm.fake import FakeEmbeddingProvider, FakeLLMProvider
from tests.conftest import Fixture


@pytest.fixture(autouse=True)
async def _dispose_db_engine_after_integration(
    request: pytest.FixtureRequest,
) -> AsyncIterator[None]:
    """search 多路 session 后释放连接池，避免 asyncpg 跨 event loop。"""
    yield
    if "fixture_data" in request.fixturenames:
        from app.platform.db import dispose_engine

        await dispose_engine()


async def _seed_empty_kb(fixture_data: Fixture) -> uuid.UUID:
    async with session_scope(
        tenant_id=fixture_data.primary_tenant_id, user_id=fixture_data.user_id
    ) as session:
        kb = KnowledgeBase(
            tenant_id=fixture_data.primary_tenant_id,
            name="查询扩展测试库",
            embedding_model="fake",
            embedding_dim=1024,
            created_by=fixture_data.user_id,
        )
        session.add(kb)
        await session.flush()
        return kb.id


async def _seed_chunk_kb(
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
            name="查询扩展召回库",
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
            storage_key=f"tenants/{fixture_data.primary_tenant_id}/documents/{uuid7()}/expand.txt",
            status="ready",
            page_count=1,
            uploaded_by=fixture_data.user_id,
        )
        session.add(doc)
        await session.flush()
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
        return kb.id, chunk.id


def _silence_usage_recording(monkeypatch: pytest.MonkeyPatch) -> None:
    """避免 search 内 _record_usage 额外开 session，导致 asyncpg 跨 event loop 复用连接。"""

    async def _noop(self, **kwargs):
        return None

    monkeypatch.setattr(RetrievalService, "_record_usage", _noop)


def test_should_expand_disabled() -> None:
    assert should_expand(enabled=False, fused=[]) is False
    assert should_expand(enabled=False, fused=[("a", 0.001)]) is False


def test_should_expand_empty_hits() -> None:
    assert should_expand(enabled=True, fused=[]) is True


def test_should_expand_low_top_rrf() -> None:
    assert should_expand(enabled=True, fused=[("a", EXPAND_RRF_FLOOR - 1e-6)]) is True
    assert should_expand(enabled=True, fused=[("a", 0.01)]) is True


def test_should_expand_high_top_rrf() -> None:
    # 两路都靠前时 RRF ≈ 1/61 + 1/61 ≈ 0.0328
    assert should_expand(enabled=True, fused=[("a", EXPAND_RRF_FLOOR)]) is False
    assert should_expand(enabled=True, fused=[("a", 0.032)]) is False


@pytest.mark.asyncio
async def test_fake_llm_expand_fixture() -> None:
    llm = FakeLLMProvider()
    result = await llm.chat(
        [
            Message(role="system", content="你是查询扩展助手，只输出改写问句。"),
            Message(role="user", content="泵压力多少"),
        ]
    )
    assert "HYD-2201" in result.content
    assert "额定" in result.content or "压力" in result.content


@pytest.mark.asyncio
async def test_expand_query_returns_fixed_rewrite() -> None:
    llm = FakeLLMProvider()
    out = await expand_query(llm, query="泵压力多少")
    assert out is not None
    assert "HYD-2201" in out


@pytest.mark.asyncio
async def test_expand_query_failure_returns_none() -> None:
    class Boom:
        name = "boom"

        async def chat(self, messages, **opts):
            raise RuntimeError("upstream down")

    assert await expand_query(Boom(), query="x") is None  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_search_query_expand_rewrites_on_weak_recall(
    fixture_data: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """弱召回（空 fused）时 search 应调用 Fake 扩展并写入 rewritten_query。"""
    _silence_usage_recording(monkeypatch)
    kb_id = await _seed_empty_kb(fixture_data)
    query = "泵压力多少"
    q_norm = normalize(query)

    async with session_scope(
        tenant_id=fixture_data.primary_tenant_id, user_id=fixture_data.user_id
    ) as session:
        service = RetrievalService(session, FakeEmbeddingProvider(dimension=1024))
        result = await service.search(
            tenant_id=fixture_data.primary_tenant_id,
            user_id=fixture_data.user_id,
            role=ROLE_OWNER,
            query=query,
            kb_ids=[kb_id],
            top_k=5,
            options=SearchOptions(query_expand=True),
            llm=FakeLLMProvider(),
        )

    assert result.rewritten_query != q_norm
    assert "HYD-2201" in result.rewritten_query
    assert "额定" in result.rewritten_query or "压力" in result.rewritten_query


@pytest.mark.asyncio
async def test_search_query_expand_disabled_keeps_normalized_query(
    fixture_data: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """query_expand=False 时不调用 LLM，rewritten_query 保持 normalize(query)。"""
    _silence_usage_recording(monkeypatch)
    kb_id = await _seed_empty_kb(fixture_data)
    query = "泵压力多少"
    q_norm = normalize(query)

    class BoomLLM:
        name = "boom"

        async def chat(self, messages, **opts):
            raise AssertionError("query_expand=False 时不应调用 LLM")

    async with session_scope(
        tenant_id=fixture_data.primary_tenant_id, user_id=fixture_data.user_id
    ) as session:
        service = RetrievalService(session, FakeEmbeddingProvider(dimension=1024))
        result = await service.search(
            tenant_id=fixture_data.primary_tenant_id,
            user_id=fixture_data.user_id,
            role=ROLE_OWNER,
            query=query,
            kb_ids=[kb_id],
            top_k=5,
            options=SearchOptions(query_expand=False),
            llm=BoomLLM(),  # type: ignore[arg-type]
        )

    assert result.rewritten_query == q_norm


@pytest.mark.asyncio
async def test_search_query_expand_second_channel_failure_keeps_first_result(
    fixture_data: Fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """二次召回失败时保留首次融合命中，rewritten_query 不改为扩展问句。"""
    _silence_usage_recording(monkeypatch)
    kb_id, chunk_id = await _seed_chunk_kb(fixture_data)
    query = "泵压力多少"
    q_norm = normalize(query)
    calls = {"n": 0}

    async def patched_channel(self, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            vec = [RankedHit(chunk_id=chunk_id, score=0.3)]
            fused = [(str(chunk_id), EXPAND_RRF_FLOOR - 1e-3)]
            return vec, [], fused, 1.0, 1.0
        raise RuntimeError("second channel down")

    monkeypatch.setattr(RetrievalService, "_channel_search", patched_channel)

    async with session_scope(
        tenant_id=fixture_data.primary_tenant_id, user_id=fixture_data.user_id
    ) as session:
        service = RetrievalService(session, FakeEmbeddingProvider(dimension=1024))
        result = await service.search(
            tenant_id=fixture_data.primary_tenant_id,
            user_id=fixture_data.user_id,
            role=ROLE_OWNER,
            query=query,
            kb_ids=[kb_id],
            top_k=5,
            options=SearchOptions(query_expand=True),
            llm=FakeLLMProvider(),
        )

    assert calls["n"] == 2
    assert result.rewritten_query == q_norm
    assert any(h.chunk_id == chunk_id for h in result.hits)
