"""审计 API 的请求/响应模型。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID | None
    action: str
    target_type: str
    target_id: uuid.UUID | None
    payload: dict[str, Any] = Field(default_factory=dict)
    ip: str | None = None
    created_at: datetime

    @field_validator("ip", mode="before")
    @classmethod
    def _ip_to_str(cls, value: Any) -> str | None:
        if value is None:
            return None
        return str(value)


class AuditLogList(BaseModel):
    items: list[AuditLogOut]
    total: int
