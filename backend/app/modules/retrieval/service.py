"""混合检索编排。"""

from __future__ import annotations

import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ingestion.chunkers.tsv import build_tsv
from app.modules.ingestion.parsers.normalize import normalize
from app.modules.retrieval.base import SearchHit, SearchOptions, SearchResult
from app.modules.retrieval.expand import expand_hits, load_document_titles
from app.modules.retrieval.repository import RetrievalRepository
from app.modules.retrieval.rrf import rrf_fuse
from app.platform.errors import NotFound
from app.platform.llm.base import EmbeddingProvider


class RetrievalService:
    def __init__(
        self,
        session: AsyncSession,
        embedding: EmbeddingProvider,
        *,
        repo: RetrievalRepository | None = None,
    ) -> None:
        self._session = session
        self._embedding = embedding
        self._repo = repo or RetrievalRepository(session)

    async def search(
        self,
        *,
        tenant_id: uuid.UUID,
        query: str,
        kb_ids: list[uuid.UUID] | None,
        top_k: int = 8,
        options: SearchOptions | None = None,
    ) -> SearchResult:
        opts = options or SearchOptions()
        t0 = time.perf_counter()

        visible = await self._repo.list_visible_kb_ids(tenant_id)
        visible_set = set(visible)
        if kb_ids is None or len(kb_ids) == 0:
            resolved = visible
        else:
            unknown = [i for i in kb_ids if i not in visible_set]
            if unknown:
                raise NotFound("知识库不存在或不可见")
            resolved = list(kb_ids)

        q_norm = normalize(query)
        tsv_q = build_tsv(q_norm)

        emb_t0 = time.perf_counter()
        vectors = await self._embedding.embed([q_norm], input_type="query")
        query_vec = vectors[0]
        # 向量与全文串行即可（同 session）；耗时分别统计
        vec_hits = await self._repo.vector_search(
            tenant_id=tenant_id,
            kb_ids=resolved,
            query_vec=query_vec,
            limit=opts.candidate_n,
        )
        vector_ms = (time.perf_counter() - emb_t0) * 1000

        ft_t0 = time.perf_counter()
        ft_hits = await self._repo.fulltext_search(
            tenant_id=tenant_id,
            kb_ids=resolved,
            tsv_query=tsv_q,
            limit=opts.candidate_n,
        )
        fulltext_ms = (time.perf_counter() - ft_t0) * 1000

        vec_scores = {str(h.chunk_id): h.score for h in vec_hits}
        ft_scores = {str(h.chunk_id): h.score for h in ft_hits}
        fused = rrf_fuse(
            [[str(h.chunk_id) for h in vec_hits], [str(h.chunk_id) for h in ft_hits]],
            k=60,
        )
        rrf_scores = {cid: score for cid, score in fused}
        top_ids = [uuid.UUID(cid) for cid, _ in fused[:30]]

        expanded = await expand_hits(
            self._session,
            tenant_id=tenant_id,
            seed_chunk_ids=top_ids[: max(top_k, 8)],
            n=opts.expand_context,
        )
        # 生成用：优先 RRF 序的种子，再补 expand；最终截断 top_k
        by_id = {c.id: c for c in expanded}
        ordered: list = []
        seen: set[uuid.UUID] = set()
        for cid in top_ids:
            if cid in by_id and cid not in seen:
                ordered.append(by_id[cid])
                seen.add(cid)
        for c in expanded:
            if c.id not in seen:
                ordered.append(c)
                seen.add(c.id)
        ordered = ordered[:top_k]

        titles = await load_document_titles(
            self._session, [c.document_id for c in ordered]
        )
        hits: list[SearchHit] = []
        for c in ordered:
            cid = str(c.id)
            hits.append(
                SearchHit(
                    chunk_id=c.id,
                    document_id=c.document_id,
                    document_title=titles.get(c.document_id, ""),
                    kb_id=c.kb_id,
                    heading_path=list(c.heading_path or []),
                    content=c.content,
                    page_start=c.page_start,
                    page_end=c.page_end,
                    bboxes=list(c.bboxes or []),
                    chunk_type=c.chunk_type,
                    seq=c.seq,
                    scores={
                        "vector": vec_scores.get(cid),
                        "fulltext": ft_scores.get(cid),
                        "rrf": rrf_scores.get(cid),
                        "rerank": None,
                    },
                )
            )

        total_ms = (time.perf_counter() - t0) * 1000
        return SearchResult(
            hits=hits,
            stats={
                "vector_ms": round(vector_ms, 2),
                "fulltext_ms": round(fulltext_ms, 2),
                "rerank_ms": 0.0,
                "total_ms": round(total_ms, 2),
            },
            rewritten_query=q_norm,
        )
