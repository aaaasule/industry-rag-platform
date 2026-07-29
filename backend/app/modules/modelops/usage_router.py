"""用量查询 HTTP 接口。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.modules.identity.models import ROLE_ADMIN
from app.modules.modelops.usage_schemas import (
    UsageBreakdownOut,
    UsageSeriesOut,
    UsageSummaryOut,
)
from app.modules.modelops.usage_service import UsageQueryService
from app.platform.deps import ClaimsDep, TenantSessionDep, require_role

router = APIRouter(
    prefix="/usages",
    tags=["usages"],
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)


def _service(session: TenantSessionDep) -> UsageQueryService:
    return UsageQueryService(session)


ServiceDep = Depends(_service)


@router.get("/summary", response_model=UsageSummaryOut)
async def usage_summary(
    claims: ClaimsDep,
    period: Literal["day", "week", "month"] = "month",
    timezone: str = Query(default="Asia/Shanghai"),
    service: UsageQueryService = ServiceDep,
) -> UsageSummaryOut:
    return await service.summary(claims, period=period, timezone=timezone)


@router.get("/series", response_model=UsageSeriesOut)
async def usage_series(
    claims: ClaimsDep,
    from_time: datetime = Query(alias="from"),
    to_time: datetime = Query(alias="to"),
    timezone: str = Query(...),
    granularity: Literal["hour", "day"] = "day",
    group_by: Literal["purpose", "model", "connection_id"] = "purpose",
    service: UsageQueryService = ServiceDep,
) -> UsageSeriesOut:
    return await service.series(
        claims,
        from_time=from_time,
        to_time=to_time,
        timezone=timezone,
        granularity=granularity,
        group_by=group_by,
    )


@router.get("/breakdown", response_model=UsageBreakdownOut)
async def usage_breakdown(
    claims: ClaimsDep,
    from_time: datetime = Query(alias="from"),
    to_time: datetime = Query(alias="to"),
    dimension: Literal["model", "purpose", "connection"] = "model",
    metric: Literal["cost", "call_count", "prompt_tokens"] = "cost",
    top: int = Query(default=10, ge=1, le=50),
    service: UsageQueryService = ServiceDep,
) -> UsageBreakdownOut:
    return await service.breakdown(
        claims,
        from_time=from_time,
        to_time=to_time,
        dimension=dimension,
        metric=metric,
        top=top,
    )
