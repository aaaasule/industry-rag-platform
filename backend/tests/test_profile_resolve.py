"""EffectiveProfile 合并与 resolve 单元测试。"""

from __future__ import annotations

from app.modules.ingestion.chunkers.structure import chunk_pages
from app.modules.profile.schemas import DEFAULT_CHUNK_RULES, ChunkRulesConfig
from app.modules.profile.service import (
    merge_chunk_rules,
    shallow_merge,
    to_ingestion_chunk_rules,
)


def test_shallow_merge_right_wins() -> None:
    assert shallow_merge({"a": 1, "b": 2}, {"b": 9, "c": 3}) == {"a": 1, "b": 9, "c": 3}
    assert shallow_merge(None, {"a": 1}, None) == {"a": 1}


def test_merge_chunk_rules_priority_kb_over_profile_over_default() -> None:
    profile = {
        "max_tokens": 400,
        "clause_mode": True,
        "min_tokens": 50,
    }
    kb_settings = {
        "chunk_rules": {
            "max_tokens": 256,
            # clause_mode 未覆盖 → 保留 profile True
        }
    }
    cfg = merge_chunk_rules(profile_rules=profile, kb_settings=kb_settings)
    assert cfg.max_tokens == 256
    assert cfg.clause_mode is True
    assert cfg.min_tokens == 50
    assert cfg.overlap_tokens == DEFAULT_CHUNK_RULES.overlap_tokens


def test_merge_chunk_rules_defaults_when_empty() -> None:
    cfg = merge_chunk_rules(profile_rules=None, kb_settings=None)
    assert cfg == DEFAULT_CHUNK_RULES


def test_general_vs_process_industry_clause_mode_distinguishable() -> None:
    """builtin 种子语义：general 不分条款；process_industry 条款模式可切出更多块。"""
    pages = [
        {
            "page_no": 1,
            "blocks": [
                {
                    "text": "4.1.1本条款规定操作步骤与注意事项，内容足够长以通过最小 token。" * 3,
                    "bbox": [72, 100, 500, 140],
                    "size": 12,
                },
                {
                    "text": "4.1.2后续条款继续描述安全要求与检查项目，同样需要足够长度。" * 3,
                    "bbox": [72, 160, 500, 200],
                    "size": 12,
                },
            ],
        }
    ]
    general = merge_chunk_rules(
        profile_rules={
            "max_tokens": 512,
            "min_tokens": 5,
            "overlap_tokens": 64,
            "clause_mode": False,
        },
        kb_settings=None,
    )
    process = merge_chunk_rules(
        profile_rules={
            "max_tokens": 512,
            "min_tokens": 5,
            "overlap_tokens": 64,
            "clause_mode": True,
        },
        kb_settings=None,
    )
    assert general.clause_mode is False
    assert process.clause_mode is True

    general_drafts = chunk_pages(pages, to_ingestion_chunk_rules(general), title="规程")
    process_drafts = chunk_pages(pages, to_ingestion_chunk_rules(process), title="规程")
    assert len(process_drafts) > len(general_drafts)


def test_to_ingestion_chunk_rules_maps_fields() -> None:
    cfg = ChunkRulesConfig(
        max_tokens=100,
        min_tokens=20,
        overlap_tokens=10,
        clause_mode=True,
        keep_heading_prefix=False,
    )
    rules = to_ingestion_chunk_rules(cfg)
    assert rules.max_tokens == 100
    assert rules.min_tokens == 20
    assert rules.overlap_tokens == 10
    assert rules.clause_mode is True
    assert rules.keep_heading_prefix is False
