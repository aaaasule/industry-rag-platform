"""混合检索编排。"""

from __future__ import annotations

import time
import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.permissions import PERM_READ, visible_kb_ids
from app.modules.ingestion.chunkers.tsv import build_tsv
from app.modules.ingestion.parsers.normalize import normalize
from app.modules.retrieval.base import SearchHit, SearchOptions, SearchResult
from app.modules.retrieval.expand import expand_hits, load_document_titles
from app.modules.retrieval.repository import RetrievalRepository
from app.modules.retrieval.rrf import rrf_fuse
from app.modules.retrieval.synonyms import apply_synonyms, coerce_synonyms
from app.platform.errors import NotFound
from app.platform.llm.base import EmbeddingProvider, RerankProvider


class RetrievalService:
    def __init__(
        self,
        session: AsyncSession,
        embedding: EmbeddingProvider,
        *,
        repo: RetrievalRepository | None = None,
        rerank: RerankProvider | None = None,
    ) -> None:
        self._session = session
        self._embedding = embedding
        self._repo = repo or RetrievalRepository(session)
        self._rerank = rerank

    async def search(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        query: str,
        kb_ids: list[uuid.UUID] | None,
        top_k: int = 8,
        options: SearchOptions | None = None,
        dictionary: Sequence[str] | None = None,
        synonyms: Any = None,
    ) -> SearchResult:
        opts = options or SearchOptions()
        t0 = time.perf_counter()

        visible = await visible_kb_ids(
            self._session,
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            permission=PERM_READ,
        )
        visible_set = set(visible)
        if kb_ids is None or len(kb_ids) == 0:
            resolved = visible
        else:
            unknown = [i for i in kb_ids if i not in visible_set]
            if unknown:
                raise NotFound("知识库不存在或不可见")
            resolved = list(kb_ids)

        q_norm = normalize(query)
        q_norm = apply_synonyms(q_norm, coerce_synonyms(synonyms))
        tsv_q = build_tsv(q_norm, dictionary=dictionary)

        emb_t0 = time.perf_counter()
        vectors = await self._embedding.embed([q_norm], input_type="query")
        emb_ms = int((time.perf_counter() - emb_t0) * 1000)
        await self._record_usage(
            tenant_id=tenant_id,
            user_id=user_id,
            purpose="embedding",
            texts=[q_norm],
            latency_ms=emb_ms,
            success=True,
            kb_id=resolved[0] if resolved else None,
        )
        query_vec = vectors[0]
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

        # 重排候选：RRF Top 池，再截断 top_k
        candidates = ordered[: max(top_k, min(30, len(ordered)))]
        rerank_scores: dict[str, float] = {}
        rerank_ms = 0.0
        if opts.rerank and self._rerank is not None and candidates:
            rr_t0 = time.perf_counter()
            docs = [c.content for c in candidates]
            scored = await self._rerank.rerank(q_norm, docs, top_n=min(top_k, len(docs)))
            rerank_ms = (time.perf_counter() - rr_t0) * 1000
            await self._record_usage(
                tenant_id=tenant_id,
                user_id=user_id,
                purpose="rerank",
                texts=[q_norm, *docs],
                latency_ms=int(rerank_ms),
                success=True,
                kb_id=resolved[0] if resolved else None,
            )
            reranked: list = []
            used: set[uuid.UUID] = set()
            for item in scored:
                if 0 <= item.index < len(candidates):
                    chunk = candidates[item.index]
                    if chunk.id in used:
                        continue
                    reranked.append(chunk)
                    used.add(chunk.id)
                    rerank_scores[str(chunk.id)] = item.score
            for c in candidates:
                if c.id not in used:
                    reranked.append(c)
            ordered = reranked[:top_k]
        else:
            ordered = candidates[:top_k]

        titles = await load_document_titles(self._session, [c.document_id for c in ordered])
        hits: list[SearchHit] = []
        for c in ordered:
            chunk_key = str(c.id)
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
                        "vector": vec_scores.get(chunk_key),
                        "fulltext": ft_scores.get(chunk_key),
                        "rrf": rrf_scores.get(chunk_key),
                        "rerank": rerank_scores.get(chunk_key),
                    },
                )
            )

        total_ms = (time.perf_counter() - t0) * 1000
        return SearchResult(
            hits=hits,
            stats={
                "vector_ms": round(vector_ms, 2),
                "fulltext_ms": round(fulltext_ms, 2),
                "rerank_ms": round(rerank_ms, 2),
                "total_ms": round(total_ms, 2),
            },
            rewritten_query=q_norm,
        )

    async def _record_usage(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        purpose: str,
        texts: list[str],
        latency_ms: int,
        success: bool,
        kb_id: uuid.UUID | None,
        error_code: str | None = None,
    ) -> None:
        from app.modules.modelops.usage_recorder import (
            UsageRecorder,
            estimate_tokens,
            resolve_usage_route,
        )

        conn_id, provider_type, model = await resolve_usage_route(self._session, tenant_id, purpose)
        prompt_tokens = sum(estimate_tokens(t) for t in texts)
        await UsageRecorder.record(
            tenant_id=tenant_id,
            user_id=user_id,
            connection_id=conn_id,
            kb_id=kb_id,
            purpose=purpose,
            provider_type=provider_type,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            latency_ms=latency_ms,
            success=success,
            error_code=error_code,
        )
