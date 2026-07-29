"""Chunk 召回 SQL。"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import Chunk, Document, KnowledgeBase
from app.modules.retrieval.base import RankedHit


class RetrievalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_visible_kb_ids(self, tenant_id: uuid.UUID) -> list[uuid.UUID]:
        rows = (
            (
                await self._session.execute(
                    select(KnowledgeBase.id).where(
                        KnowledgeBase.tenant_id == tenant_id,
                        KnowledgeBase.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
        return list(rows)

    async def vector_search(
        self,
        *,
        tenant_id: uuid.UUID,
        kb_ids: list[uuid.UUID],
        query_vec: list[float],
        limit: int,
    ) -> list[RankedHit]:
        if not kb_ids:
            return []
        distance = Chunk.embedding.cosine_distance(query_vec)
        stmt: Select[Any] = (
            select(Chunk.id, distance.label("distance"))
            .join(Document, Document.id == Chunk.document_id)
            .where(
                Chunk.tenant_id == tenant_id,
                Chunk.kb_id.in_(kb_ids),
                Document.deleted_at.is_(None),
                Document.status == "ready",
            )
            .order_by(distance)
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [RankedHit(chunk_id=r[0], score=max(0.0, 1.0 - float(r[1]))) for r in rows]

    async def fulltext_search(
        self,
        *,
        tenant_id: uuid.UUID,
        kb_ids: list[uuid.UUID],
        tsv_query: str,
        limit: int,
    ) -> list[RankedHit]:
        if not kb_ids or not tsv_query.strip():
            return []
        ts_query = func.plainto_tsquery("simple", tsv_query)
        rank = func.ts_rank_cd(Chunk.tsv, ts_query)
        stmt = (
            select(Chunk.id, rank.label("rank"))
            .join(Document, Document.id == Chunk.document_id)
            .where(
                Chunk.tenant_id == tenant_id,
                Chunk.kb_id.in_(kb_ids),
                Document.deleted_at.is_(None),
                Document.status == "ready",
                Chunk.tsv.op("@@")(ts_query),
            )
            .order_by(rank.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [RankedHit(chunk_id=r[0], score=float(r[1] or 0.0)) for r in rows]
