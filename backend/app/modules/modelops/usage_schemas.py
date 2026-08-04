"""用量查询 API 的请求/响应。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class UsageSummaryOut(BaseModel):
    period: dict[str, str]
    total_tokens: int
    total_cost: float
    call_count: int
    success_rate: float
    quota: dict[str, Any] | None = None
    compare_previous: dict[str, float] = Field(default_factory=dict)
    currency: str = "USD"
    stale_until: datetime | None = None


class SeriesPoint(BaseModel):
    t: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0
    call_count: int = 0
    success_rate: float = 1.0
    latency_p95_ms: int | None = None


class SeriesGroup(BaseModel):
    group: dict[str, str]
    points: list[SeriesPoint]


class UsageSeriesOut(BaseModel):
    granularity: Literal["hour", "day"]
    timezone: str
    series: list[SeriesGroup]
    currency: str = "USD"
    stale_until: datetime | None = None


class BreakdownItem(BaseModel):
    key: str
    label: str
    value: float
    share: float
    call_count: int


class UsageBreakdownOut(BaseModel):
    items: list[BreakdownItem]
    others: dict[str, float]
    total: float
    currency: str = "USD"
    stale_until: datetime | None = None


def dec_to_float(v: Decimal | float | int | None) -> float:
    if v is None:
        return 0.0
    return float(v)
