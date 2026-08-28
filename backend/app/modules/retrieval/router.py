"""检索 HTTP 接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.modules.modelops.provider_factory import ProviderFactory
from app.modules.profile.service import resolve_for_kb_ids, resolve_rerank_enabled
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
from app.platform.deps import (
    ClaimsDep,
    ResolvedEmbeddingDep,
    ResolvedRerankDep,
    SettingsDep,
    TenantSessionDep,
    require_search_rate_limit,
    require_token_quota,
)
from app.platform.llm.base import LLMProvider

router = APIRouter(tags=["retrieval"])


def _service(
    session: TenantSessionDep, embedding: ResolvedEmbeddingDep, rerank: ResolvedRerankDep
) -> RetrievalService:
    return RetrievalService(session, embedding, repo=RetrievalRepository(session), rerank=rerank)


ServiceDep = Depends(_service)


async def _optional_llm(
    session: TenantSessionDep, claims: ClaimsDep, *, enabled: bool
) -> LLMProvider | None:
    """仅在查询扩展开启时解析 LLM；失败返回 None（扩展降级为首次结果）。"""
    if not enabled:
        return None
    try:
        return await ProviderFactory(session).get_llm(claims.tenant_id)
    except Exception:
        return None


@router.post(
    "/search",
    response_model=SearchResponse,
    dependencies=[Depends(require_search_rate_limit), Depends(require_token_quota)],
)
async def search(
    payload: SearchRequest,
    claims: ClaimsDep,
    settings: SettingsDep,
    session: TenantSessionDep,
    service: RetrievalService = ServiceDep,
) -> SearchResponse:
    effective = await resolve_for_kb_ids(session, payload.kb_ids)
    if "rerank" in payload.options:
        rerank = bool(payload.options["rerank"])
    else:
        rerank = resolve_rerank_enabled(
            effective.retrieval_rules, env_default=settings.effective_rerank_default
        )
    top_k = payload.top_k if payload.top_k is not None else effective.retrieval_rules.top_k
    if "query_expand" in payload.options:
        query_expand = bool(payload.options["query_expand"])
    else:
        query_expand = effective.retrieval_rules.query_expand
    opts = SearchOptions(
        expand_context=int(payload.options.get("expand_context", 1)),
        rerank=rerank,
        query_expand=query_expand,
    )
    dictionary = effective.parse_rules.get("dictionary")
    synonyms = effective.parse_rules.get("synonyms")
    llm = await _optional_llm(session, claims, enabled=query_expand)
    result = await service.search(
        tenant_id=claims.tenant_id,
        user_id=claims.user_id,
        role=claims.role,
        query=payload.query,
        kb_ids=payload.kb_ids,
        top_k=top_k,
        options=opts,
        dictionary=dictionary,
        synonyms=synonyms,
        llm=llm,
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
