"""知识库 settings 白名单校验。"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from app.modules.profile.schemas import ChunkRulesConfig, RetrievalRulesConfig
from app.platform.errors import UnprocessableState

_ALLOWED_TOP = frozenset({"chunk_rules", "retrieval_rules"})
_ALLOWED_CHUNK = frozenset(
    {"max_tokens", "min_tokens", "overlap_tokens", "clause_mode", "keep_heading_prefix"}
)
_ALLOWED_RETRIEVAL = frozenset({"top_k", "rerank_enabled", "query_expand"})


def validate_kb_settings(raw: dict[str, Any]) -> dict[str, Any]:
    """校验并返回可写入的 settings；未知键 → 422 settings_invalid。"""
    if not isinstance(raw, dict):
        raise UnprocessableState("settings 必须为对象", code="settings_invalid")

    unknown_top = set(raw) - _ALLOWED_TOP
    if unknown_top:
        raise UnprocessableState(
            f"settings 含未允许字段: {', '.join(sorted(unknown_top))}",
            code="settings_invalid",
        )

    out: dict[str, Any] = {}
    if "chunk_rules" in raw:
        chunk = raw["chunk_rules"]
        if not isinstance(chunk, dict):
            raise UnprocessableState("chunk_rules 必须为对象", code="settings_invalid")
        unknown = set(chunk) - _ALLOWED_CHUNK
        if unknown:
            raise UnprocessableState(
                f"chunk_rules 含未允许字段: {', '.join(sorted(unknown))}",
                code="settings_invalid",
            )
        out["chunk_rules"] = _validate_chunk_rules(chunk)

    if "retrieval_rules" in raw:
        ret = raw["retrieval_rules"]
        if not isinstance(ret, dict):
            raise UnprocessableState("retrieval_rules 必须为对象", code="settings_invalid")
        unknown = set(ret) - _ALLOWED_RETRIEVAL
        if unknown:
            raise UnprocessableState(
                f"retrieval_rules 含未允许字段: {', '.join(sorted(unknown))}",
                code="settings_invalid",
            )
        out["retrieval_rules"] = _validate_retrieval_rules(ret)

    return out


def _validate_chunk_rules(chunk: dict[str, Any]) -> dict[str, Any]:
    try:
        validated = ChunkRulesConfig.model_validate(chunk)
    except ValidationError as exc:
        raise UnprocessableState(
            "chunk_rules 字段值无效",
            code="settings_invalid",
            details={"errors": exc.errors()},
        ) from exc
    return validated.model_dump(exclude_unset=True)


def _validate_retrieval_rules(ret: dict[str, Any]) -> dict[str, Any]:
    try:
        validated = RetrievalRulesConfig.model_validate(ret)
    except ValidationError as exc:
        raise UnprocessableState(
            "retrieval_rules 字段值无效",
            code="settings_invalid",
            details={"errors": exc.errors()},
        ) from exc
    return validated.model_dump(exclude_unset=True)
