"""检索领域类型。"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SearchOptions:
    expand_context: int = 1
    rerank: bool = False
    candidate_n: int = 50
    min_score_threshold: float = 0.35
    # None：未指定（视为关闭）；True/False：请求或 Profile 决议后的开关
    query_expand: bool | None = None


@dataclass
class RankedHit:
    chunk_id: uuid.UUID
    score: float


@dataclass
class SearchHit:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    kb_id: uuid.UUID
    heading_path: list[str]
    content: str
    page_start: int
    page_end: int
    bboxes: list[dict[str, Any]]
    chunk_type: str
    seq: int
    scores: dict[str, float | None] = field(default_factory=dict)


@dataclass
class SearchResult:
    hits: list[SearchHit]
    stats: dict[str, float]
    rewritten_query: str
