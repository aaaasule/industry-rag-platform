"""用量查询（读 hourlies / 概览）。"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import Tenant, User
from app.modules.knowledge.models import KnowledgeBase
from app.modules.modelops.usage_models import LlmUsage, LlmUsageHourly
from app.modules.modelops.usage_recorder import HOURLIES_UNTIL_KEY
from app.modules.modelops.usage_schemas import (
    BreakdownItem,
    SeriesGroup,
    SeriesPoint,
    UsageBreakdownOut,
    UsageSeriesOut,
    UsageSummaryOut,
    dec_to_float,
)
from app.platform.config import get_settings
from app.platform.errors import AppError
from app.platform.security import TokenClaims

BreakdownDimension = Literal["model", "purpose", "connection", "user", "knowledge_base"]


class UsageQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def summary(
        self,
        claims: TokenClaims,
        *,
        period: Literal["day", "week", "month"] = "month",
        timezone: str = "Asia/Shanghai",
    ) -> UsageSummaryOut:
        tz = ZoneInfo(timezone)
        now = datetime.now(tz)
        start, end = _period_bounds(now, period)
        prev_start, prev_end = _previous_period(start, end)

        cur = await self._aggregate_range(
            claims.tenant_id, start.astimezone(UTC), end.astimezone(UTC)
        )
        prev = await self._aggregate_range(
            claims.tenant_id, prev_start.astimezone(UTC), prev_end.astimezone(UTC)
        )

        compare: dict[str, float] = {}
        if prev["total_tokens"] > 0:
            compare["total_tokens"] = round(
                (cur["total_tokens"] - prev["total_tokens"]) / prev["total_tokens"], 4
            )
        else:
            compare["total_tokens"] = 0.0
        if prev["total_cost"] > 0:
            compare["total_cost"] = round(
                (cur["total_cost"] - prev["total_cost"]) / prev["total_cost"], 4
            )
        else:
            compare["total_cost"] = 0.0

        tenant = await self._session.get(Tenant, claims.tenant_id)
        quota_out = None
        if tenant is not None:
            limit = int((tenant.quota or {}).get("monthly_tokens") or 0)
            if limit > 0:
                quota_out = {
                    "token_limit": limit,
                    "used_ratio": round(cur["total_tokens"] / limit, 4),
                    "reset_at": (end + timedelta(seconds=1)).isoformat(),
                }

        return UsageSummaryOut(
            period={"from": start.date().isoformat(), "to": end.date().isoformat()},
            total_tokens=cur["total_tokens"],
            total_cost=cur["total_cost"],
            call_count=cur["call_count"],
            success_rate=cur["success_rate"],
            quota=quota_out,
            compare_previous=compare,
            stale_until=_stale_until(),
        )

    async def series(
        self,
        claims: TokenClaims,
        *,
        from_time: datetime,
        to_time: datetime,
        timezone: str,
        granularity: Literal["hour", "day"] = "day",
        group_by: Literal["purpose", "model", "connection_id"] = "purpose",
    ) -> UsageSeriesOut:
        if granularity == "hour" and (to_time - from_time) > timedelta(days=7):
            raise AppError("跨度超过 7 天时不能使用 hour 粒度", code="validation_error")

        tz = ZoneInfo(timezone)
        rows = await self._hourlies(
            claims.tenant_id, from_time.astimezone(UTC), to_time.astimezone(UTC)
        )
        buckets: dict[str, dict[str, dict[str, Any]]] = defaultdict(
            lambda: defaultdict(
                lambda: {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "cost": 0.0,
                    "call_count": 0,
                    "success_count": 0,
                    "latency_p95_ms": None,
                }
            )
        )
        for r in rows:
            local = r.bucket_hour.astimezone(tz)
            if granularity == "day":
                key_t = local.date().isoformat()
            else:
                key_t = local.replace(minute=0, second=0, microsecond=0).isoformat()
            if group_by == "purpose":
                g = r.purpose
            elif group_by == "model":
                g = r.model
            else:
                g = str(r.connection_id)
            cell = buckets[g][key_t]
            cell["prompt_tokens"] += int(r.prompt_tokens)
            cell["completion_tokens"] += int(r.completion_tokens)
            cell["cost"] += dec_to_float(r.cost)
            cell["call_count"] += int(r.call_count)
            cell["success_count"] += int(r.success_count)
            # 日/小时桶内多行 hourlies：取 max(p95) 作为近似（非精确合并分位数）
            if r.latency_p95_ms is not None:
                prev = cell["latency_p95_ms"]
                cell["latency_p95_ms"] = (
                    int(r.latency_p95_ms) if prev is None else max(int(prev), int(r.latency_p95_ms))
                )

        series: list[SeriesGroup] = []
        for g, points_map in sorted(buckets.items()):
            points = []
            for t in sorted(points_map.keys()):
                c = points_map[t]
                rate = (c["success_count"] / c["call_count"]) if c["call_count"] else 1.0
                points.append(
                    SeriesPoint(
                        t=t,
                        prompt_tokens=c["prompt_tokens"],
                        completion_tokens=c["completion_tokens"],
                        cost=round(c["cost"], 6),
                        call_count=c["call_count"],
                        success_rate=round(rate, 4),
                        latency_p95_ms=c["latency_p95_ms"],
                    )
                )
            series.append(SeriesGroup(group={group_by: g}, points=points))

        return UsageSeriesOut(
            granularity=granularity,
            timezone=timezone,
            series=series,
            stale_until=_stale_until(),
        )

    async def breakdown(
        self,
        claims: TokenClaims,
        *,
        from_time: datetime,
        to_time: datetime,
        dimension: BreakdownDimension = "model",
        metric: Literal["cost", "call_count", "prompt_tokens"] = "cost",
        top: int = 10,
    ) -> UsageBreakdownOut:
        start = from_time.astimezone(UTC)
        end = to_time.astimezone(UTC)
        if dimension == "user" or dimension == "knowledge_base":
            totals, labels = await self._breakdown_from_usages(
                claims.tenant_id, start, end, dimension=dimension, metric=metric
            )
        else:
            totals, labels = await self._breakdown_from_hourlies(
                claims.tenant_id, start, end, dimension=dimension, metric=metric
            )

        ranked = sorted(totals.items(), key=lambda x: x[1]["value"], reverse=True)
        top_items = ranked[:top]
        rest = ranked[top:]
        total_val = sum(v["value"] for _, v in ranked) or 0.0
        items = [
            BreakdownItem(
                key=k,
                label=labels.get(k, k),
                value=round(v["value"], 6),
                share=round(v["value"] / total_val, 4) if total_val else 0.0,
                call_count=int(v["call_count"]),
            )
            for k, v in top_items
        ]
        others_val = sum(v["value"] for _, v in rest)
        return UsageBreakdownOut(
            items=items,
            others={
                "value": round(others_val, 6),
                "share": round(others_val / total_val, 4) if total_val else 0.0,
            },
            total=round(total_val, 6),
            stale_until=_stale_until(),
        )

    async def _breakdown_from_hourlies(
        self,
        tenant_id: uuid.UUID,
        start: datetime,
        end: datetime,
        *,
        dimension: Literal["model", "purpose", "connection"],
        metric: Literal["cost", "call_count", "prompt_tokens"],
    ) -> tuple[dict[str, dict[str, float]], dict[str, str]]:
        rows = await self._hourlies(tenant_id, start, end)
        totals: dict[str, dict[str, float]] = defaultdict(lambda: {"value": 0.0, "call_count": 0})
        for r in rows:
            if dimension == "model":
                key = r.model
            elif dimension == "purpose":
                key = r.purpose
            else:
                key = str(r.connection_id)
            if metric == "cost":
                totals[key]["value"] += dec_to_float(r.cost)
            elif metric == "call_count":
                totals[key]["value"] += float(r.call_count)
            else:
                totals[key]["value"] += float(r.prompt_tokens)
            totals[key]["call_count"] += float(r.call_count)
        return totals, {k: k for k in totals}

    async def _breakdown_from_usages(
        self,
        tenant_id: uuid.UUID,
        start: datetime,
        end: datetime,
        *,
        dimension: Literal["user", "knowledge_base"],
        metric: Literal["cost", "call_count", "prompt_tokens"],
    ) -> tuple[dict[str, dict[str, float]], dict[str, str]]:
        """Top 用户/KB：明细表短时窗聚合（hourlies 无这两维）。"""
        stmt = select(LlmUsage).where(
            LlmUsage.tenant_id == tenant_id,
            LlmUsage.created_at >= start,
            LlmUsage.created_at < end,
        )
        usages = list((await self._session.execute(stmt)).scalars().all())
        totals: dict[str, dict[str, float]] = defaultdict(lambda: {"value": 0.0, "call_count": 0})
        for u in usages:
            raw_id = u.user_id if dimension == "user" else u.kb_id
            key = "unknown" if raw_id is None else str(raw_id)
            if metric == "cost":
                totals[key]["value"] += dec_to_float(u.cost)
            elif metric == "call_count":
                totals[key]["value"] += 1.0
            else:
                totals[key]["value"] += float(u.prompt_tokens)
            totals[key]["call_count"] += 1.0

        labels = await self._resolve_breakdown_labels(tenant_id, dimension, list(totals.keys()))
        return totals, labels

    async def _resolve_breakdown_labels(
        self,
        tenant_id: uuid.UUID,
        dimension: Literal["user", "knowledge_base"],
        keys: list[str],
    ) -> dict[str, str]:
        labels = {k: k for k in keys}
        labels["unknown"] = "未归因"
        ids: list[uuid.UUID] = []
        for k in keys:
            if k == "unknown":
                continue
            try:
                ids.append(uuid.UUID(k))
            except ValueError:
                continue
        if not ids:
            return labels
        if dimension == "user":
            users = list(
                (await self._session.execute(select(User).where(User.id.in_(ids)))).scalars().all()
            )
            for u in users:
                labels[str(u.id)] = u.display_name or u.email
        else:
            kbs = list(
                (
                    await self._session.execute(
                        select(KnowledgeBase).where(
                            KnowledgeBase.tenant_id == tenant_id,
                            KnowledgeBase.id.in_(ids),
                        )
                    )
                )
                .scalars()
                .all()
            )
            for kb in kbs:
                labels[str(kb.id)] = kb.name
        return labels

    async def _hourlies(
        self, tenant_id: uuid.UUID, start: datetime, end: datetime
    ) -> list[LlmUsageHourly]:
        stmt = (
            select(LlmUsageHourly)
            .where(
                LlmUsageHourly.tenant_id == tenant_id,
                LlmUsageHourly.bucket_hour >= start,
                LlmUsageHourly.bucket_hour < end,
            )
            .order_by(LlmUsageHourly.bucket_hour.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def _aggregate_range(
        self, tenant_id: uuid.UUID, start: datetime, end: datetime
    ) -> dict[str, Any]:
        rows = await self._hourlies(tenant_id, start, end)
        if rows:
            call_count = sum(r.call_count for r in rows)
            success = sum(r.success_count for r in rows)
            tokens = sum(r.prompt_tokens + r.completion_tokens for r in rows)
            cost = sum(dec_to_float(r.cost) for r in rows)
        else:
            stmt2 = select(LlmUsage).where(
                LlmUsage.tenant_id == tenant_id,
                LlmUsage.created_at >= start,
                LlmUsage.created_at < end,
            )
            usages = list((await self._session.execute(stmt2)).scalars().all())
            call_count = len(usages)
            success = sum(1 for u in usages if u.success)
            tokens = sum(u.prompt_tokens + u.completion_tokens for u in usages)
            cost = sum(dec_to_float(u.cost) for u in usages)

        return {
            "total_tokens": int(tokens),
            "total_cost": round(float(cost), 6),
            "call_count": int(call_count),
            "success_rate": round(success / call_count, 4) if call_count else 1.0,
        }


def _period_bounds(now: datetime, period: str) -> tuple[datetime, datetime]:
    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now


def _previous_period(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    delta = end - start
    return start - delta, start


def _stale_until() -> datetime | None:
    try:
        client = redis.from_url(get_settings().redis_url, decode_responses=True)
        raw = client.get(HOURLIES_UNTIL_KEY)
        if isinstance(raw, str) and raw:
            return datetime.fromisoformat(raw)
    except Exception:
        return None
    return None
