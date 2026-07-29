"""模型接入点 ORM（02 文档 §4.8）。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.identity.models import JSONColumn
from app.platform.db import Base, TimestampMixin, UUIDPrimaryKeyMixin

PURPOSE_CHAT = "chat"
PURPOSE_EMBEDDING = "embedding"
PURPOSE_RERANK = "rerank"
PURPOSE_TITLE = "title"
PURPOSES = (PURPOSE_CHAT, PURPOSE_EMBEDDING, PURPOSE_RERANK, PURPOSE_TITLE)

PROVIDER_FAKE = "fake"
PROVIDER_OPENAI_COMPATIBLE = "openai_compatible"
PROVIDER_TYPES = (PROVIDER_FAKE, PROVIDER_OPENAI_COMPATIBLE)

HEALTH_UNKNOWN = "unknown"
HEALTH_HEALTHY = "healthy"
HEALTH_DEGRADED = "degraded"
HEALTH_DOWN = "down"


class ModelConnection(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "model_connections"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    provider_type: Mapped[str] = mapped_column(Text, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    credential_cipher: Mapped[str] = mapped_column(Text, nullable=False, default="")
    credential_hint: Mapped[str] = mapped_column(Text, nullable=False, default="")
    model: Mapped[str] = mapped_column(Text, nullable=False)
    purposes: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    health: Mapped[str] = mapped_column(Text, nullable=False, default=HEALTH_UNKNOWN)
    health_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    extra: Mapped[dict[str, Any]] = mapped_column(JSONColumn, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    @property
    def is_platform(self) -> bool:
        return self.tenant_id is None
