"""行业配置四级回退：KB.settings → IndustryProfile → 代码默认。"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ingestion.chunkers.structure import ChunkRules
from app.modules.knowledge.models import IndustryProfile, KnowledgeBase
from app.modules.profile.schemas import (
    DEFAULT_CHUNK_RULES,
    DEFAULT_PROMPT_OVERRIDES,
    DEFAULT_RETRIEVAL_RULES,
    ChunkRulesConfig,
    EffectiveProfile,
    PromptOverridesConfig,
    RetrievalRulesConfig,
)


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    return {}


def shallow_merge(*layers: dict[str, Any] | None) -> dict[str, Any]:
    """从左到右浅合并；右侧覆盖左侧。None / 非 dict 视为 {}。"""
    out: dict[str, Any] = {}
    for layer in layers:
        if not layer:
            continue
        if not isinstance(layer, dict):
            continue
        out.update(layer)
    return out


def merge_chunk_rules(
    *,
    profile_rules: dict[str, Any] | None,
    kb_settings: dict[str, Any] | None,
) -> ChunkRulesConfig:
    kb = _as_dict(kb_settings)
    kb_chunk = _as_dict(kb.get("chunk_rules"))
    merged = shallow_merge(
        DEFAULT_CHUNK_RULES.model_dump(),
        _as_dict(profile_rules),
        kb_chunk,
    )
    return ChunkRulesConfig.model_validate(merged)


def merge_retrieval_rules(
    *,
    profile_rules: dict[str, Any] | None,
    kb_settings: dict[str, Any] | None,
) -> RetrievalRulesConfig:
    kb = _as_dict(kb_settings)
    kb_ret = _as_dict(kb.get("retrieval_rules"))
    merged = shallow_merge(
        DEFAULT_RETRIEVAL_RULES.model_dump(exclude_none=True),
        _as_dict(profile_rules),
        kb_ret,
    )
    return RetrievalRulesConfig.model_validate(merged)


def merge_prompt_overrides(
    *,
    profile_overrides: dict[str, Any] | None,
    kb_settings: dict[str, Any] | None,
) -> PromptOverridesConfig:
    kb = _as_dict(kb_settings)
    kb_prompt = _as_dict(kb.get("prompt_overrides"))
    merged = shallow_merge(
        DEFAULT_PROMPT_OVERRIDES.model_dump(exclude_none=True),
        _as_dict(profile_overrides),
        kb_prompt,
    )
    return PromptOverridesConfig.model_validate(merged)


def to_ingestion_chunk_rules(cfg: ChunkRulesConfig) -> ChunkRules:
    """映射到摄取侧 dataclass（结构分块器入参）。"""
    return ChunkRules(
        max_tokens=cfg.max_tokens,
        min_tokens=cfg.min_tokens,
        overlap_tokens=cfg.overlap_tokens,
        clause_mode=cfg.clause_mode,
        keep_heading_prefix=cfg.keep_heading_prefix,
    )


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve(self, kb_id: uuid.UUID) -> EffectiveProfile:
        """按知识库解析生效配置。

        优先级（高 → 低）：
        1. KnowledgeBase.settings 内对应域（如 chunk_rules）
        2. IndustryProfile 对应 jsonb 列
        3. 代码默认（schemas.DEFAULT_*）
        """
        result = await self._session.execute(
            select(KnowledgeBase, IndustryProfile)
            .outerjoin(IndustryProfile, KnowledgeBase.profile_id == IndustryProfile.id)
            .where(KnowledgeBase.id == kb_id)
        )
        row = result.one_or_none()
        if row is None:
            return EffectiveProfile()

        kb, profile = row
        settings = _as_dict(kb.settings)

        # 已软删的 profile 视为缺失，回退到无 profile（防御性；正常路径删除前会拦 in_use）
        if profile is not None and profile.deleted_at is not None:
            profile = None

        if profile is None:
            return EffectiveProfile(
                chunk_rules=merge_chunk_rules(profile_rules=None, kb_settings=settings),
                parse_rules=_as_dict(settings.get("parse_rules")),
                metadata_schema=_as_dict(settings.get("metadata_schema")),
                prompt_overrides=merge_prompt_overrides(
                    profile_overrides=None, kb_settings=settings
                ),
                retrieval_rules=merge_retrieval_rules(profile_rules=None, kb_settings=settings),
            )

        # parse_rules / metadata_schema：整域替换（KB 有则用 KB，否则用 profile）
        parse_rules = (
            _as_dict(settings["parse_rules"])
            if "parse_rules" in settings
            else _as_dict(profile.parse_rules)
        )
        metadata_schema = (
            _as_dict(settings["metadata_schema"])
            if "metadata_schema" in settings
            else _as_dict(profile.metadata_schema)
        )

        return EffectiveProfile(
            profile_id=profile.id,
            code=profile.code,
            name=profile.name,
            is_builtin=profile.is_builtin,
            chunk_rules=merge_chunk_rules(
                profile_rules=_as_dict(profile.chunk_rules),
                kb_settings=settings,
            ),
            parse_rules=parse_rules,
            metadata_schema=metadata_schema,
            prompt_overrides=merge_prompt_overrides(
                profile_overrides=_as_dict(profile.prompt_overrides),
                kb_settings=settings,
            ),
            retrieval_rules=merge_retrieval_rules(
                profile_rules=_as_dict(profile.retrieval_rules),
                kb_settings=settings,
            ),
        )


async def resolve_effective_profile(session: AsyncSession, kb_id: uuid.UUID) -> EffectiveProfile:
    return await ProfileService(session).resolve(kb_id)


def primary_kb_id(kb_ids: list[uuid.UUID] | None) -> uuid.UUID | None:
    """多 KB 时取首个（与 usage 埋点约定一致）。"""
    if not kb_ids:
        return None
    return kb_ids[0]


def resolve_rerank_enabled(rules: RetrievalRulesConfig, *, env_default: bool) -> bool:
    """profile.rerank_enabled 优先；None 时回退环境默认。"""
    if rules.rerank_enabled is not None:
        return bool(rules.rerank_enabled)
    return env_default


async def resolve_for_kb_ids(
    session: AsyncSession, kb_ids: list[uuid.UUID] | None
) -> EffectiveProfile:
    kb_id = primary_kb_id(kb_ids)
    if kb_id is None:
        return EffectiveProfile()
    return await resolve_effective_profile(session, kb_id)
