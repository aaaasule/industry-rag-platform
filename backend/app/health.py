"""存活与就绪探针。

healthz 只表示进程活着（不查依赖，否则数据库抖动会引发无谓的容器重启）；
readyz 才检查依赖，用于流量摘除。这个区分是 K8s 探针语义的要求。
"""

from __future__ import annotations

import asyncio
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.platform.config import get_settings
from app.platform.db import get_sessionmaker
from app.platform.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["system"])

_PROBE_TIMEOUT = 3.0


@router.get("/healthz", summary="存活探针")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz", summary="就绪探针")
async def readyz(response: Response) -> dict[str, Any]:
    checks = dict(
        zip(
            ("database", "redis"),
            await asyncio.gather(_check_database(), _check_redis()),
            strict=True,
        )
    )
    ready = all(v == "ok" for v in checks.values())
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "ok" if ready else "degraded", "checks": checks}


async def _check_database() -> str:
    try:
        async with asyncio.timeout(_PROBE_TIMEOUT), get_sessionmaker()() as session:
            await session.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:
        logger.warning("readiness_database_failed", error=str(exc))
        return "failed"


async def _check_redis() -> str:
    client = aioredis.from_url(get_settings().redis_url)
    try:
        async with asyncio.timeout(_PROBE_TIMEOUT):
            await client.ping()
        return "ok"
    except Exception as exc:
        logger.warning("readiness_redis_failed", error=str(exc))
        return "failed"
    finally:
        await client.aclose()
