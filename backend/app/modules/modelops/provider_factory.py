"""按用途解析接入点并缓存 Provider 实例。"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modelops.models import (
    HEALTH_DOWN,
    PURPOSE_CHAT,
    PURPOSE_EMBEDDING,
    PURPOSE_RERANK,
    PURPOSE_TITLE,
    ModelConnection,
)
from app.modules.modelops.repository import ModelConnectionRepository
from app.modules.modelops.schemas import RouteHit, RoutesOut
from app.platform.config import Settings, get_settings
from app.platform.llm.base import EmbeddingProvider, LLMProvider, RerankProvider
from app.platform.llm.factory import (
    build_embedding_from_connection,
    build_embedding_provider,
    build_llm_from_connection,
    build_llm_provider,
    build_rerank_from_connection,
    build_rerank_provider,
)

Purpose = Literal["chat", "embedding", "rerank", "title"]

_provider_cache: dict[tuple[uuid.UUID, int, str], Any] = {}


class ProviderFactory:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings | None = None,
        *,
        repo: ModelConnectionRepository | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._repo = repo or ModelConnectionRepository(session)

    async def resolve_connection(
        self, purpose: Purpose, tenant_id: uuid.UUID
    ) -> tuple[ModelConnection | None, Literal["tenant", "platform", "env"]]:
        rows = await self._repo.list_for_purpose(tenant_id=tenant_id, purpose=purpose)
        usable = [r for r in rows if r.health != HEALTH_DOWN]
        if not usable:
            return None, "env"
        row = usable[0]
        source: Literal["tenant", "platform"] = (
            "tenant" if row.tenant_id == tenant_id else "platform"
        )
        return row, source

    async def get_llm(self, tenant_id: uuid.UUID) -> LLMProvider:
        conn, _ = await self.resolve_connection(PURPOSE_CHAT, tenant_id)
        if conn is None:
            # title 可回退 chat；此处 chat 直接 env
            return build_llm_provider(self._settings)
        return self._cached(conn, "llm", build_llm_from_connection)

    async def get_embedding(self, tenant_id: uuid.UUID) -> EmbeddingProvider:
        conn, _ = await self.resolve_connection(PURPOSE_EMBEDDING, tenant_id)
        if conn is None:
            return build_embedding_provider(self._settings)
        return self._cached(conn, "embedding", build_embedding_from_connection)

    async def get_rerank(self, tenant_id: uuid.UUID) -> RerankProvider:
        conn, _ = await self.resolve_connection(PURPOSE_RERANK, tenant_id)
        if conn is None:
            return build_rerank_provider(self._settings)
        return self._cached(conn, "rerank", build_rerank_from_connection)

    async def routes(self, tenant_id: uuid.UUID) -> RoutesOut:
        items: list[RouteHit] = []
        for purpose in (PURPOSE_CHAT, PURPOSE_EMBEDDING, PURPOSE_RERANK, PURPOSE_TITLE):
            conn, source = await self.resolve_connection(purpose, tenant_id)  # type: ignore[arg-type]
            if conn is None:
                items.append(self._env_route(purpose))
            else:
                items.append(
                    RouteHit(
                        purpose=purpose,
                        source=source,
                        connection_id=conn.id,
                        name=conn.name,
                        provider_type=conn.provider_type,
                        model=conn.model,
                        priority=conn.priority,
                    )
                )
        return RoutesOut(items=items)

    def _env_route(self, purpose: str) -> RouteHit:
        s = self._settings
        if purpose == PURPOSE_EMBEDDING:
            return RouteHit(
                purpose=purpose,
                source="env",
                provider_type=s.embedding_provider,
                model=s.embedding_model,
            )
        if purpose == PURPOSE_RERANK:
            return RouteHit(
                purpose=purpose,
                source="env",
                provider_type=s.resolved_rerank_provider,
                model=s.rerank_model,
            )
        return RouteHit(
            purpose=purpose,
            source="env",
            provider_type=s.llm_provider,
            model=s.llm_model,
        )

    def _cached(
        self,
        conn: ModelConnection,
        kind: str,
        builder: Any,
    ) -> Any:
        key = (conn.id, conn.version, kind)
        cached = _provider_cache.get(key)
        if cached is not None:
            return cached
        provider = builder(conn, settings=self._settings)
        _provider_cache[key] = provider
        return provider


def clear_provider_cache() -> None:
    _provider_cache.clear()
