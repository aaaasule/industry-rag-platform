"""切片 B：prompt / retrieval 消费 EffectiveProfile。"""

from __future__ import annotations

import uuid

from app.modules.chat.prompts import SYSTEM_PROMPT, build_messages
from app.modules.profile.schemas import RetrievalRulesConfig
from app.modules.profile.service import (
    merge_retrieval_rules,
    primary_kb_id,
    resolve_rerank_enabled,
)
from app.modules.retrieval.base import SearchHit


def _hit() -> SearchHit:
    return SearchHit(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_title="手册",
        kb_id=uuid.uuid4(),
        heading_path=["1 总则"],
        content="示例证据内容",
        page_start=1,
        page_end=1,
        bboxes=[],
        chunk_type="text",
        seq=0,
        scores={"rrf": 0.5},
    )


def test_build_messages_uses_system_override() -> None:
    override = "你是流程工业助手。"
    msgs = build_messages("问什么？", [_hit()], system_override=override)
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"].startswith(override)
    assert "证据：" in msgs[0]["content"]
    assert SYSTEM_PROMPT not in msgs[0]["content"]


def test_build_messages_falls_back_to_default_system() -> None:
    msgs = build_messages("问什么？", [_hit()], system_override=None)
    assert msgs[0]["content"].startswith(SYSTEM_PROMPT.strip())


def test_build_messages_blank_override_uses_default() -> None:
    msgs = build_messages("问什么？", [_hit()], system_override="   ")
    assert msgs[0]["content"].startswith(SYSTEM_PROMPT.strip())


def test_primary_kb_id_picks_first() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    assert primary_kb_id([a, b]) == a
    assert primary_kb_id([]) is None
    assert primary_kb_id(None) is None


def test_resolve_rerank_enabled_profile_over_env() -> None:
    assert resolve_rerank_enabled(RetrievalRulesConfig(rerank_enabled=True), env_default=False)
    assert not resolve_rerank_enabled(RetrievalRulesConfig(rerank_enabled=False), env_default=True)
    assert resolve_rerank_enabled(RetrievalRulesConfig(rerank_enabled=None), env_default=True)


def test_process_industry_retrieval_top_k_differs_from_general() -> None:
    general = merge_retrieval_rules(profile_rules={"top_k": 8}, kb_settings=None)
    process = merge_retrieval_rules(profile_rules={"top_k": 10}, kb_settings=None)
    assert general.top_k == 8
    assert process.top_k == 10
