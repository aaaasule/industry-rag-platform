"""聊天请求/响应模型。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    kb_ids: list[uuid.UUID] = Field(min_length=1)
    title: str = Field(default="新会话", max_length=200)


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kb_ids: list[uuid.UUID]
    title: str
    created_at: datetime
    updated_at: datetime


class CitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    index_no: int
    chunk_id: uuid.UUID | None
    document_id: uuid.UUID
    quote: str
    page_start: int
    bboxes: list[dict[str, Any]]
    score: float


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    status: str
    citations: list[CitationOut] = Field(default_factory=list)
    created_at: datetime


class ChatCompletionRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    kb_ids: list[uuid.UUID] | None = None
    message: str = Field(min_length=1, max_length=8000)
    options: dict[str, Any] = Field(default_factory=dict)
