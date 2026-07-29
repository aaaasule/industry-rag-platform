"""modelops 请求/响应模型。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Purpose = Literal["chat", "embedding", "rerank", "title"]
ProviderType = Literal["openai_compatible", "fake"]


class ModelConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    provider_type: ProviderType = "openai_compatible"
    base_url: str = Field(min_length=1, max_length=512)
    model: str = Field(min_length=1, max_length=128)
    purposes: list[Purpose] = Field(min_length=1)
    priority: int = Field(default=100, ge=0, le=10_000)
    enabled: bool = True
    api_key: str | None = Field(default=None, max_length=512)
    extra: dict[str, Any] = Field(default_factory=dict)


class ModelConnectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    base_url: str | None = Field(default=None, min_length=1, max_length=512)
    model: str | None = Field(default=None, min_length=1, max_length=128)
    purposes: list[Purpose] | None = Field(default=None, min_length=1)
    priority: int | None = Field(default=None, ge=0, le=10_000)
    enabled: bool | None = None
    extra: dict[str, Any] | None = None


class CredentialUpdate(BaseModel):
    api_key: str = Field(min_length=1, max_length=512)


class ModelConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    scope: Literal["platform", "tenant"]
    name: str
    provider_type: str
    base_url: str
    model: str
    purposes: list[str]
    priority: int
    enabled: bool
    health: str
    health_checked_at: datetime | None
    credential_masked: str
    version: int
    extra: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ConnectionTestResult(BaseModel):
    ok: bool
    latency_ms: float | None = None
    model_echo: str | None = None
    error_code: str | None = None
    error_message: str | None = None


class RouteHit(BaseModel):
    purpose: str
    source: Literal["tenant", "platform", "env"]
    connection_id: uuid.UUID | None = None
    name: str | None = None
    provider_type: str
    model: str
    priority: int | None = None


class RoutesOut(BaseModel):
    items: list[RouteHit]
