"""行业配置解析（EffectiveProfile / resolve）。"""

from app.modules.profile.schemas import EffectiveProfile
from app.modules.profile.service import (
    ProfileService,
    primary_kb_id,
    resolve_effective_profile,
    resolve_for_kb_ids,
    resolve_rerank_enabled,
)

__all__ = [
    "EffectiveProfile",
    "ProfileService",
    "primary_kb_id",
    "resolve_effective_profile",
    "resolve_for_kb_ids",
    "resolve_rerank_enabled",
]
