"""租户月度 Token 配额检查。"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import Tenant
from app.modules.modelops.usage_models import LlmUsage, LlmUsageHourly
from app.platform.config import get_settings
from app.platform.errors import QuotaExceeded
from app.platform.logging import get_logger

logger = get_logger(__name__)

CACHE_TTL_SECONDS = 300
DEFAULT_TIMEZONE = "Asia/Shanghai"


class QuotaService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def check_monthly_tokens(
        self,
        tenant_id: uuid.UUID,
        *,
        timezone: str = DEFAULT_TIMEZONE,
    ) -> None:
        tenant = await self._session.get(Tenant, tenant_id)
        if tenant is None:
            return
        limit = int((tenant.quota or {}).get("monthly_tokens") or 0)
        if limit <= 0:
            return

        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            reset_at = month_start.replace(year=month_start.year + 1, month=1)
        else:
            reset_at = month_start.replace(month=month_start.month + 1)

        month_key = month_start.strftime("%Y-%m")
        cache_key = f"irp:quota:{tenant_id}:{month_key}"
        used = self._cache_get(cache_key)
        if used is None:
            used = await self._sum_tokens(
                tenant_id,
                month_start.astimezone(UTC),
                reset_at.astimezone(UTC),
            )
            self._cache_set(cache_key, used, limit)

        if used >= limit:
            retry_after = max(0, int((reset_at - now).total_seconds()))
            raise QuotaExceeded(
                details={
                    "used": used,
                    "limit": limit,
                    "reset_at": reset_at.isoformat(),
                },
                retry_after_seconds=retry_after,
            )

    async def _sum_tokens(self, tenant_id: uuid.UUID, start: datetime, end: datetime) -> int:
        rows = list(
            (
                await self._session.execute(
                    select(LlmUsageHourly).where(
                        LlmUsageHourly.tenant_id == tenant_id,
                        LlmUsageHourly.bucket_hour >= start,
                        LlmUsageHourly.bucket_hour < end,
                    )
                )
            )
            .scalars()
            .all()
        )
        if rows:
            return int(sum(r.prompt_tokens + r.completion_tokens for r in rows))

        usages = list(
            (
                await self._session.execute(
                    select(LlmUsage).where(
                        LlmUsage.tenant_id == tenant_id,
                        LlmUsage.created_at >= start,
                        LlmUsage.created_at < end,
                    )
                )
            )
            .scalars()
            .all()
        )
        return int(sum(u.prompt_tokens + u.completion_tokens for u in usages))

    @staticmethod
    def _cache_get(key: str) -> int | None:
        try:
            client = redis.from_url(get_settings().redis_url, decode_responses=True)
            raw = client.get(key)
            if not raw:
                return None
            data = json.loads(raw)
            return int(data.get("used", 0))
        except Exception as exc:
            logger.warning("quota_cache_get_failed", error=str(exc))
            return None

    @staticmethod
    def _cache_set(key: str, used: int, limit: int) -> None:
        try:
            client = redis.from_url(get_settings().redis_url, decode_responses=True)
            client.set(
                key,
                json.dumps({"used": used, "limit": limit}, ensure_ascii=False),
                ex=CACHE_TTL_SECONDS,
            )
        except Exception as exc:
            logger.warning("quota_cache_set_failed", error=str(exc))
