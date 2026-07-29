"""检索 HTTP 接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.modules.retrieval.base import SearchOptions
from app.modules.retrieval.repository import RetrievalRepository
from app.modules.retrieval.schemas import (
    HitScores,
    SearchHitOut,
    SearchRequest,
    SearchResponse,
    SearchStats,
)
from app.modules.retrieval.service import RetrievalService
from app.platform.deps import ClaimsDep, EmbeddingDep, RerankDep, SettingsDep, TenantSessionDep

router = APIRouter(tags=["retrieval"])


def _service(
    session: TenantSessionDep, embedding: EmbeddingDep, rerank: RerankDep
) -> RetrievalService:
    return RetrievalService(session, embedding, repo=RetrievalRepository(session), rerank=rerank)


ServiceDep = Depends(_service)


@router.post("/search", response_model=SearchResponse)
async def search(
    payload: SearchRequest,
    claims: ClaimsDep,
    settings: SettingsDep,
    service: RetrievalService = ServiceDep,
) -> SearchResponse:
    rerank_default = settings.effective_rerank_default
    opts = SearchOptions(
        expand_context=int(payload.options.get("expand_context", 1)),
        rerank=bool(payload.options.get("rerank", rerank_default)),
    )
    result = await service.search(
        tenant_id=claims.tenant_id,
        user_id=claims.user_id,
        role=claims.role,
        query=payload.query,
        kb_ids=payload.kb_ids,
        top_k=payload.top_k,
        options=opts,
    )
    return SearchResponse(
        query=result.rewritten_query,
        results=[
            SearchHitOut(
                chunk_id=h.chunk_id,
                document_id=h.document_id,
                document_title=h.document_title,
                heading_path=h.heading_path,
                content=h.content,
                page_start=h.page_start,
                page_end=h.page_end,
                bboxes=h.bboxes,
                scores=HitScores(**h.scores),
            )
            for h in result.hits
        ],
        stats=SearchStats(**result.stats),
    )
