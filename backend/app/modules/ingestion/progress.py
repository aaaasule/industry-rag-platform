"""摄取进度：Redis 细粒度 + 可选落库比例。"""

from __future__ import annotations

import json
import uuid
from typing import Any

import redis

from app.platform.config import Settings

_KEY = "irp:ingest:progress:{job_id}"
_TTL_SECONDS = 3600


def progress_key(job_id: uuid.UUID | str) -> str:
    return _KEY.format(job_id=str(job_id))


def write_progress(
    settings: Settings,
    job_id: uuid.UUID | str,
    *,
    stage: str,
    progress: float,
    page_done: int | None = None,
    page_total: int | None = None,
    chunk_done: int | None = None,
    chunk_total: int | None = None,
    status: str | None = None,
    error_code: str | None = None,
    error_detail: str | None = None,
    retryable: bool | None = None,
    chunk_count: int | None = None,
    duration_ms: int | None = None,
) -> None:
    payload: dict[str, Any] = {
        "stage": stage,
        "progress": max(0.0, min(1.0, float(progress))),
    }
    if page_done is not None:
        payload["page_done"] = page_done
    if page_total is not None:
        payload["page_total"] = page_total
    if chunk_done is not None:
        payload["chunk_done"] = chunk_done
    if chunk_total is not None:
        payload["chunk_total"] = chunk_total
    if status is not None:
        payload["status"] = status
    if error_code is not None:
        payload["error_code"] = error_code
    if error_detail is not None:
        payload["error_detail"] = error_detail
    if retryable is not None:
        payload["retryable"] = retryable
    if chunk_count is not None:
        payload["chunk_count"] = chunk_count
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms

    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.setex(progress_key(job_id), _TTL_SECONDS, json.dumps(payload, ensure_ascii=False))
    except Exception:
        # 进度失败不阻断摄取
        return


def read_progress(settings: Settings, job_id: uuid.UUID | str) -> dict[str, Any] | None:
    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        raw = client.get(progress_key(job_id))
        if not raw:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def clear_progress(settings: Settings, job_id: uuid.UUID | str) -> None:
    try:
        client = redis.from_url(settings.redis_url, decode_responses=True)
        client.delete(progress_key(job_id))
    except Exception:
        return
