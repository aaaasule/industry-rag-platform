"""用量与定价 ORM。"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, Numeric, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, UUIDPrimaryKeyMixin

# hourlies 主键中表示「无接入点」
NIL_CONNECTION_ID = uuid.UUID(int=0)


class ModelPricing(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "model_pricing"
    __table_args__ = (
        UniqueConstraint(
            "provider_type", "model", "effective_from", name="uq_model_pricing_provider_model_from"
        ),
    )

    provider_type: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_price_per_1k: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    completion_price_per_1k: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="USD")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LlmUsage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "llm_usages"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    connection_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    kb_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    provider_type: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, default=Decimal("0"))
    currency: Mapped[str] = mapped_column(Text, nullable=False, default="USD")
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LlmUsageHourly(Base):
    __tablename__ = "llm_usage_hourlies"

    tenant_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    bucket_hour: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    model: Mapped[str] = mapped_column(Text, primary_key=True)
    purpose: Mapped[str] = mapped_column(Text, primary_key=True)
    connection_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    call_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    cost: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False, default=Decimal("0"))
    latency_p95_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
