"""用量事件非阻塞写入 Redis。"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.config import get_settings
from app.platform.logging import get_logger

logger = get_logger(__name__)

USAGE_BUFFER_KEY = "irp:usage:buffer"
HOURLIES_UNTIL_KEY = "irp:usage:hourlies_until"


def _estimate_tokens(text: str) -> int:
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return max(1, cjk + max(1, (len(text) - cjk) // 4))


async def resolve_usage_route(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    purpose: str,
) -> tuple[uuid.UUID | None, str, str]:
    """返回 (connection_id, provider_type, model)；env 回退时 connection_id 为 None。"""
    from app.modules.modelops.provider_factory import ProviderFactory

    factory = ProviderFactory(session)
    conn, _ = await factory.resolve_connection(purpose, tenant_id)  # type: ignore[arg-type]
    if conn is not None:
        return conn.id, conn.provider_type, conn.model
    hit = factory._env_route(purpose)
    return None, hit.provider_type, hit.model


class UsageRecorder:
    """调用点只调 record；失败绝不抛出。"""

    @staticmethod
    async def record(
        *,
        tenant_id: uuid.UUID,
        purpose: str,
        provider_type: str,
        model: str,
        latency_ms: int,
        success: bool,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        user_id: uuid.UUID | None = None,
        connection_id: uuid.UUID | None = None,
        kb_id: uuid.UUID | None = None,
        error_code: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        event: dict[str, Any] = {
            "tenant_id": str(tenant_id),
            "user_id": str(user_id) if user_id else None,
            "connection_id": str(connection_id) if connection_id else None,
            "kb_id": str(kb_id) if kb_id else None,
            "purpose": purpose,
            "provider_type": provider_type,
            "model": model,
            "prompt_tokens": int(prompt_tokens),
            "completion_tokens": int(completion_tokens),
            "latency_ms": int(latency_ms),
            "success": bool(success),
            "error_code": error_code,
            "created_at": (created_at or datetime.now(UTC)).isoformat(),
        }
        try:
            client = aioredis.from_url(get_settings().redis_url, decode_responses=True)
            try:
                await client.lpush(USAGE_BUFFER_KEY, json.dumps(event, ensure_ascii=False))
            finally:
                await client.aclose()
        except Exception as exc:  # 用量失败不得影响主业务
            logger.warning("usage_record_failed", error=str(exc), purpose=purpose)


estimate_tokens = _estimate_tokens
