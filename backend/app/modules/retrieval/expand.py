"""上下文扩展：同文档 seq±n。"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import Chunk, Document


async def expand_hits(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    seed_chunk_ids: list[uuid.UUID],
    n: int,
) -> list[Chunk]:
    """对非 table 种子块拉同文档邻居，返回按 (document_id, seq) 排序的去重列表。"""
    if n <= 0 or not seed_chunk_ids:
        rows = list(
            (
                await session.execute(
                    select(Chunk).where(Chunk.tenant_id == tenant_id, Chunk.id.in_(seed_chunk_ids))
                )
            )
            .scalars()
            .all()
        )
        return sorted(rows, key=lambda c: (c.document_id, c.seq))

    seeds = list(
        (
            await session.execute(
                select(Chunk).where(Chunk.tenant_id == tenant_id, Chunk.id.in_(seed_chunk_ids))
            )
        )
        .scalars()
        .all()
    )
    wanted: set[tuple[uuid.UUID, int]] = set()
    for c in seeds:
        if c.chunk_type == "table":
            wanted.add((c.document_id, c.seq))
            continue
        for s in range(c.seq - n, c.seq + n + 1):
            if s >= 0:
                wanted.add((c.document_id, s))

    if not wanted:
        return []

    doc_ids = {d for d, _ in wanted}
    candidates = list(
        (
            await session.execute(
                select(Chunk).where(
                    Chunk.tenant_id == tenant_id,
                    Chunk.document_id.in_(doc_ids),
                )
            )
        )
        .scalars()
        .all()
    )
    out = [c for c in candidates if (c.document_id, c.seq) in wanted]
    return sorted(out, key=lambda c: (c.document_id, c.seq))


async def load_document_titles(
    session: AsyncSession, document_ids: list[uuid.UUID]
) -> dict[uuid.UUID, str]:
    if not document_ids:
        return {}
    rows = (
        await session.execute(
            select(Document.id, Document.title).where(Document.id.in_(document_ids))
        )
    ).all()
    return {r[0]: r[1] for r in rows}
