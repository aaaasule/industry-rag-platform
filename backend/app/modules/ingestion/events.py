"""文档摄取进度 SSE。"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import select

from app.modules.ingestion.progress import read_progress
from app.modules.knowledge.models import DOC_FAILED, DOC_READY, Document, IngestionJob
from app.modules.knowledge.service import KnowledgeService
from app.platform.config import Settings
from app.platform.db import session_scope
from app.platform.security import TokenClaims

_POLL_SECONDS = 0.5
_HEARTBEAT_EVERY = 15


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def iter_document_events(
    *,
    service: KnowledgeService,
    claims: TokenClaims,
    settings: Settings,
    doc_id: uuid.UUID,
) -> AsyncIterator[str]:
    """鉴权后轮询 DB + Redis，推送 progress / completed / failed。"""
    await service.get_document(claims, doc_id)
    last_payload: str | None = None
    ticks = 0

    while True:
        ticks += 1
        snapshot = await _snapshot(claims.tenant_id, claims.user_id, settings, doc_id)
        if snapshot is None:
            yield _sse(
                "failed",
                {
                    "status": "failed",
                    "error_code": "not_found",
                    "error_detail": "document missing",
                    "retryable": False,
                },
            )
            return

        event_name, payload = snapshot
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if encoded != last_payload:
            last_payload = encoded
            yield _sse(event_name, payload)
            if event_name in {"completed", "failed"}:
                return

        if ticks % _HEARTBEAT_EVERY == 0:
            yield ": heartbeat\n\n"

        await asyncio.sleep(_POLL_SECONDS)


async def _snapshot(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    settings: Settings,
    doc_id: uuid.UUID,
) -> tuple[str, dict[str, Any]] | None:
    async with session_scope(tenant_id=tenant_id, user_id=user_id) as session:
        doc = await session.get(Document, doc_id)
        if doc is None or doc.deleted_at is not None:
            return None

        job = (
            await session.execute(
                select(IngestionJob)
                .where(IngestionJob.document_id == doc_id)
                .order_by(IngestionJob.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        redis_payload = read_progress(settings, job.id) if job else None

        if doc.status == DOC_READY:
            data: dict[str, Any] = {"status": "ready"}
            if redis_payload:
                if "chunk_count" in redis_payload:
                    data["chunk_count"] = redis_payload["chunk_count"]
                if "duration_ms" in redis_payload:
                    data["duration_ms"] = redis_payload["duration_ms"]
            return "completed", data

        if doc.status == DOC_FAILED:
            return "failed", {
                "status": "failed",
                "error_code": doc.error_code
                or (job.error_code if job else None)
                or "ingest_failed",
                "error_detail": (doc.error_detail or (job.error_detail if job else None) or "")[
                    :500
                ],
                "retryable": True,
            }

        stage = "parsing"
        if doc.status == "embedding" or (job and job.stage == "embed"):
            stage = "embedding"
        if redis_payload and redis_payload.get("stage"):
            stage = str(redis_payload["stage"])

        progress = 0.0
        if redis_payload and "progress" in redis_payload:
            progress = float(redis_payload["progress"])
        elif job is not None:
            progress = float(job.progress)

        payload: dict[str, Any] = {"stage": stage, "progress": progress}
        if redis_payload:
            for key in ("page_done", "page_total", "chunk_done", "chunk_total"):
                if key in redis_payload:
                    payload[key] = redis_payload[key]
        return "progress", payload
