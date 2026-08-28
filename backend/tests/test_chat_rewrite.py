"""多轮指代消解单元测试。"""

from __future__ import annotations

import pytest

from app.modules.chat.rewrite import resolve_query
from app.platform.llm.base import Message
from app.platform.llm.fake import FakeLLMProvider


@pytest.mark.asyncio
async def test_resolve_query_rewrites_pronoun_with_history() -> None:
    llm = FakeLLMProvider()
    history = [
        ("user", "HYD-2201 的额定压力是多少？"),
        ("assistant", "根据资料，HYD-2201 额定压力为 16 MPa。[1]"),
    ]
    out = await resolve_query(llm, history=history, current="它的检修周期？")
    assert "HYD-2201" in out
    assert "检修周期" in out


@pytest.mark.asyncio
async def test_resolve_query_no_history_returns_current() -> None:
    llm = FakeLLMProvider()
    current = "它的检修周期？"
    assert await resolve_query(llm, history=[], current=current) == current


@pytest.mark.asyncio
async def test_fake_llm_coreference_fixture() -> None:
    llm = FakeLLMProvider()
    result = await llm.chat(
        [
            Message(role="system", content="你负责指代消解，只输出完整问句。"),
            Message(role="user", content="它的检修周期？"),
        ]
    )
    assert "HYD-2201" in result.content
