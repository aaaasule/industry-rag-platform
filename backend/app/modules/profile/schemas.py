"""EffectiveProfile 与各 jsonb 域的默认值。"""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class ChunkRulesConfig(BaseModel):
    max_tokens: int = 512
    min_tokens: int = 80
    overlap_tokens: int = 64
    clause_mode: bool = False
    keep_heading_prefix: bool = True


class ParseRulesConfig(BaseModel):
    """预留：OCR / 页眉页脚 / 术语表等。"""

    dictionary: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class PromptOverridesConfig(BaseModel):
    system: str | None = None

    model_config = {"extra": "allow"}


class RetrievalRulesConfig(BaseModel):
    top_k: int = 8
    rerank_enabled: bool | None = None

    model_config = {"extra": "allow"}


class EffectiveProfile(BaseModel):
    """resolve 后的生效配置（供摄取 / 检索 / 问答消费）。"""

    profile_id: uuid.UUID | None = None
    code: str = "general"
    name: str = "通用"
    is_builtin: bool = True
    chunk_rules: ChunkRulesConfig = Field(default_factory=ChunkRulesConfig)
    parse_rules: dict[str, Any] = Field(default_factory=dict)
    metadata_schema: dict[str, Any] = Field(default_factory=dict)
    prompt_overrides: PromptOverridesConfig = Field(default_factory=PromptOverridesConfig)
    retrieval_rules: RetrievalRulesConfig = Field(default_factory=RetrievalRulesConfig)


DEFAULT_CHUNK_RULES = ChunkRulesConfig()
DEFAULT_RETRIEVAL_RULES = RetrievalRulesConfig()
DEFAULT_PROMPT_OVERRIDES = PromptOverridesConfig()
