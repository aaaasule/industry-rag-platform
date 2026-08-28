"""自适应查询扩展：触发条件与 Fake LLM 夹具。"""

from __future__ import annotations

import pytest

from app.modules.retrieval.query_expand import EXPAND_RRF_FLOOR, expand_query, should_expand
from app.platform.llm.base import Message
from app.platform.llm.fake import FakeLLMProvider


def test_should_expand_disabled() -> None:
    assert should_expand(enabled=False, fused=[]) is False
    assert should_expand(enabled=False, fused=[("a", 0.001)]) is False


def test_should_expand_empty_hits() -> None:
    assert should_expand(enabled=True, fused=[]) is True


def test_should_expand_low_top_rrf() -> None:
    assert should_expand(enabled=True, fused=[("a", EXPAND_RRF_FLOOR - 1e-6)]) is True
    assert should_expand(enabled=True, fused=[("a", 0.01)]) is True


def test_should_expand_high_top_rrf() -> None:
    # 两路都靠前时 RRF ≈ 1/61 + 1/61 ≈ 0.0328
    assert should_expand(enabled=True, fused=[("a", EXPAND_RRF_FLOOR)]) is False
    assert should_expand(enabled=True, fused=[("a", 0.032)]) is False


@pytest.mark.asyncio
async def test_fake_llm_expand_fixture() -> None:
    llm = FakeLLMProvider()
    result = await llm.chat(
        [
            Message(role="system", content="你是查询扩展助手，只输出改写问句。"),
            Message(role="user", content="泵压力多少"),
        ]
    )
    assert "HYD-2201" in result.content
    assert "额定" in result.content or "压力" in result.content


@pytest.mark.asyncio
async def test_expand_query_returns_fixed_rewrite() -> None:
    llm = FakeLLMProvider()
    out = await expand_query(llm, query="泵压力多少")
    assert out is not None
    assert "HYD-2201" in out


@pytest.mark.asyncio
async def test_expand_query_failure_returns_none() -> None:
    class Boom:
        name = "boom"

        async def chat(self, messages, **opts):  # noqa: ANN001, ANN003
            raise RuntimeError("upstream down")

    assert await expand_query(Boom(), query="x") is None  # type: ignore[arg-type]
