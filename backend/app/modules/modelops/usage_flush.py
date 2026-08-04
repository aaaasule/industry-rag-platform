"""Redis 缓冲 flush 与小时预聚合。"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.modules.modelops.usage_models import (
    NIL_CONNECTION_ID,
    LlmUsage,
    LlmUsageHourly,
    ModelPricing,
)
from app.modules.modelops.usage_recorder import HOURLIES_UNTIL_KEY, USAGE_BUFFER_KEY
from app.platform.config import get_settings
from app.platform.ids import uuid7
from app.platform.logging import get_logger

logger = get_logger(__name__)

FLUSH_BATCH = 200


def _sync_redis() -> redis.Redis:
    return redis.from_url(get_settings().redis_url, decode_responses=True)


async def flush_usage_buffer(batch_size: int = FLUSH_BATCH) -> int:
    """从 Redis 弹出事件并写入 llm_usages；返回写入条数。"""
    client = _sync_redis()
    raw_items: list[str] = []
    for _ in range(batch_size):
        item = client.rpop(USAGE_BUFFER_KEY)
        if item is None:
            break
        # decode_responses=True 时应为 str；显式规范化满足类型检查
        raw_items.append(item if isinstance(item, str) else str(item))
    if not raw_items:
        return 0

    events: list[dict[str, Any]] = []
    for raw in raw_items:
        try:
            events.append(json.loads(raw))
        except json.JSONDecodeError:
            logger.warning("usage_event_invalid_json")

    settings = get_settings()
    url = settings.database_migration_url or settings.database_url
    # flush 用迁移角色绕过 RLS，按事件内 tenant_id 写入
    engine = create_async_engine(url, pool_pre_ping=True)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    written = 0
    try:
        async with maker() as session:
            pricing_cache: dict[tuple[str, str], ModelPricing | None] = {}
            for ev in events:
                try:
                    row = await _event_to_row(session, ev, pricing_cache)
                    session.add(row)
                    written += 1
                except Exception as exc:
                    logger.warning("usage_flush_row_failed", error=str(exc))
            await session.commit()
    finally:
        await engine.dispose()
    logger.info("usage_flushed", count=written)
    return written


async def _event_to_row(
    session: AsyncSession,
    ev: dict[str, Any],
    pricing_cache: dict[tuple[str, str], ModelPricing | None],
) -> LlmUsage:
    created_at = datetime.fromisoformat(ev["created_at"])
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    provider_type = ev["provider_type"]
    model = ev["model"]
    key = (provider_type, model)
    if key not in pricing_cache:
        pricing_cache[key] = await _find_pricing(session, provider_type, model, created_at)
    pricing = pricing_cache[key]
    prompt_tokens = int(ev.get("prompt_tokens") or 0)
    completion_tokens = int(ev.get("completion_tokens") or 0)
    cost = Decimal("0")
    currency = "USD"
    if pricing is not None:
        cost = (
            Decimal(prompt_tokens) / Decimal(1000) * pricing.prompt_price_per_1k
            + Decimal(completion_tokens) / Decimal(1000) * pricing.completion_price_per_1k
        ).quantize(Decimal("0.000001"))
        currency = pricing.currency

    conn_raw = ev.get("connection_id")
    return LlmUsage(
        id=uuid7(),
        tenant_id=uuid.UUID(ev["tenant_id"]),
        user_id=uuid.UUID(ev["user_id"]) if ev.get("user_id") else None,
        connection_id=uuid.UUID(conn_raw) if conn_raw else None,
        kb_id=uuid.UUID(ev["kb_id"]) if ev.get("kb_id") else None,
        purpose=ev["purpose"],
        provider_type=provider_type,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost=cost,
        currency=currency,
        latency_ms=int(ev.get("latency_ms") or 0),
        success=bool(ev.get("success")),
        error_code=ev.get("error_code"),
        created_at=created_at,
    )


async def _find_pricing(
    session: AsyncSession, provider_type: str, model: str, at: datetime
) -> ModelPricing | None:
    stmt = (
        select(ModelPricing)
        .where(
            ModelPricing.provider_type == provider_type,
            ModelPricing.model == model,
            ModelPricing.effective_from <= at,
            (ModelPricing.effective_to.is_(None)) | (ModelPricing.effective_to > at),
        )
        .order_by(ModelPricing.effective_from.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def aggregate_hourlies(*, lookback_hours: int = 48) -> int:
    """按 UTC 小时桶从 llm_usages 重算并 UPSERT hourlies。"""
    settings = get_settings()
    url = settings.database_migration_url or settings.database_url
    engine = create_async_engine(url, pool_pre_ping=True)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    since = datetime.now(UTC).replace(minute=0, second=0, microsecond=0) - timedelta(
        hours=lookback_hours
    )
    upserted = 0
    try:
        async with maker() as session:
            # 用 SQL 聚合，避免把明细拉进 Python
            result = await session.execute(
                text(
                    """
                    SELECT
                        tenant_id,
                        date_trunc('hour', created_at) AS bucket_hour,
                        model,
                        purpose,
                        COALESCE(connection_id, :nil) AS connection_id,
                        COUNT(*)::int AS call_count,
                        COUNT(*) FILTER (WHERE success)::int AS success_count,
                        COALESCE(SUM(prompt_tokens), 0)::bigint AS prompt_tokens,
                        COALESCE(SUM(completion_tokens), 0)::bigint AS completion_tokens,
                        COALESCE(SUM(cost), 0) AS cost,
                        percentile_disc(0.95) WITHIN GROUP (ORDER BY latency_ms)::int
                            AS latency_p95_ms
                    FROM llm_usages
                    WHERE created_at >= :since
                    GROUP BY 1, 2, 3, 4, 5
                    """
                ),
                {"since": since, "nil": str(NIL_CONNECTION_ID)},
            )
            rows = result.mappings().all()
            for r in rows:
                existing = await session.get(
                    LlmUsageHourly,
                    {
                        "tenant_id": r["tenant_id"],
                        "bucket_hour": r["bucket_hour"],
                        "model": r["model"],
                        "purpose": r["purpose"],
                        "connection_id": r["connection_id"],
                    },
                )
                if existing is None:
                    session.add(
                        LlmUsageHourly(
                            tenant_id=r["tenant_id"],
                            bucket_hour=r["bucket_hour"],
                            model=r["model"],
                            purpose=r["purpose"],
                            connection_id=r["connection_id"],
                            call_count=r["call_count"],
                            success_count=r["success_count"],
                            prompt_tokens=r["prompt_tokens"],
                            completion_tokens=r["completion_tokens"],
                            cost=r["cost"],
                            latency_p95_ms=r["latency_p95_ms"],
                        )
                    )
                else:
                    existing.call_count = r["call_count"]
                    existing.success_count = r["success_count"]
                    existing.prompt_tokens = r["prompt_tokens"]
                    existing.completion_tokens = r["completion_tokens"]
                    existing.cost = r["cost"]
                    existing.latency_p95_ms = r["latency_p95_ms"]
                upserted += 1
            await session.commit()
    finally:
        await engine.dispose()

    try:
        client = _sync_redis()
        client.set(HOURLIES_UNTIL_KEY, datetime.now(UTC).isoformat())
    except Exception as exc:
        logger.warning("hourlies_until_set_failed", error=str(exc))

    logger.info("hourlies_aggregated", buckets=upserted)
    return upserted
