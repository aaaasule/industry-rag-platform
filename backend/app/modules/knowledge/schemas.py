"""知识库与文档的请求/响应模型。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

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
    created_at: datetime
    updated_at: datetime


class DocumentCreated(BaseModel):
    document_id: uuid.UUID
    status: str
    job_id: uuid.UUID | None = None


class IndustryProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    is_builtin: bool
    tenant_id: uuid.UUID | None


class PreviewUrlOut(BaseModel):
    url: str
    expires_in: int


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
