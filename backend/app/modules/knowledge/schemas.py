"""知识库与文档的请求/响应模型。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class KnowledgeBaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    profile_code: str | None = Field(default="general", description="行业模板 code")
    visibility: str = Field(default="private", pattern="^(private|tenant)$")


class KnowledgeBaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    visibility: str | None = Field(default=None, pattern="^(private|tenant)$")
    profile_code: str | None = Field(
        default=None, min_length=1, max_length=100, description="改绑行业模板 code"
    )


class KnowledgeBaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    embedding_model: str
    embedding_dim: int
    visibility: str
    doc_count: int
    chunk_count: int
    profile_id: uuid.UUID | None
    created_at: datetime


class UploadUrlRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=512)
    file_size: int = Field(gt=0, le=100 * 1024 * 1024)
    mime_type: str = Field(min_length=3, max_length=128)


class UploadUrlResponse(BaseModel):
    upload_url: str
    storage_key: str
    document_id: uuid.UUID
    expires_in: int


class DocumentRegisterRequest(BaseModel):
    storage_key: str
    document_id: uuid.UUID
    title: str = Field(min_length=1, max_length=500)
    checksum: str = Field(min_length=10, max_length=128)
    file_size: int = Field(gt=0)
    mime_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentUpdate(BaseModel):
    enabled: bool | None = None
    metadata: dict[str, Any] | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kb_id: uuid.UUID
    title: str
    mime_type: str
    file_size: int
    checksum: str
    page_count: int | None
    status: str
    error_code: str | None
    error_detail: str | None
    enabled: bool = True
    chunk_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class DocumentCreated(BaseModel):
    document_id: uuid.UUID
    status: str
    job_id: uuid.UUID | None = None


class DocumentBatchRequest(BaseModel):
    action: Literal["delete", "reingest"]
    document_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)


class DocumentBatchResponse(BaseModel):
    accepted: int
    job_ids: dict[str, uuid.UUID | None]


class IndustryProfileCreate(BaseModel):
    """从 base_code 派生租户自定义模板。"""

    base_code: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    chunk_rules: dict[str, Any] | None = None
    prompt_overrides: dict[str, Any] | None = None
    retrieval_rules: dict[str, Any] | None = None
    parse_rules: dict[str, Any] | None = None
    metadata_schema: dict[str, Any] | None = None


class IndustryProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    chunk_rules: dict[str, Any] | None = None
    prompt_overrides: dict[str, Any] | None = None
    retrieval_rules: dict[str, Any] | None = None
    parse_rules: dict[str, Any] | None = None
    metadata_schema: dict[str, Any] | None = None


class IndustryProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    is_builtin: bool
    tenant_id: uuid.UUID | None
    chunk_rules: dict[str, Any] = Field(default_factory=dict)
    prompt_overrides: dict[str, Any] = Field(default_factory=dict)
    retrieval_rules: dict[str, Any] = Field(default_factory=dict)
    parse_rules: dict[str, Any] = Field(default_factory=dict)
    metadata_schema: dict[str, Any] = Field(default_factory=dict)
    deleted_at: datetime | None = None


class PreviewUrlOut(BaseModel):
    url: str
    expires_in: int


class DocumentPageOut(BaseModel):
    page_no: int
    plain_text: str
    source: str


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seq: int
    content: str
    heading_path: list[str]
    page_start: int
    page_end: int
    bboxes: list[dict[str, Any]]
    chunk_type: str


class GrantUpsert(BaseModel):
    permission: str = Field(pattern="^(read|write|manage)$")


class GrantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kb_id: uuid.UUID
    user_id: uuid.UUID
    permission: str
    created_at: datetime
    email: str | None = None
    display_name: str | None = None
