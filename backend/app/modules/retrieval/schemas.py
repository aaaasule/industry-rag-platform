"""检索 API 模型。"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    kb_ids: list[uuid.UUID] | None = None
    top_k: int = Field(default=8, ge=1, le=50)
    options: dict[str, Any] = Field(default_factory=dict)


class HitScores(BaseModel):
    vector: float | None = None
    fulltext: float | None = None
    rrf: float | None = None
    rerank: float | None = None


class SearchHitOut(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    heading_path: list[str]
    content: str
    page_start: int
    page_end: int
    bboxes: list[dict[str, Any]]
    scores: HitScores


class SearchStats(BaseModel):
    vector_ms: float
    fulltext_ms: float
    rerank_ms: float
    total_ms: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchHitOut]
    stats: SearchStats
