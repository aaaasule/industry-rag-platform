"""Provider 抽象层测试。

重点不是"Fake 返回了什么"，而是"Fake 是否满足接口契约"——它承担着后续所有
检索/生成测试的地基，行为不稳会让上层测试变成随机数。
"""

from __future__ import annotations

import math

import pytest

from app.platform.llm.base import (
    EmbeddingProvider,
    LLMProvider,
    Message,
    RerankProvider,
)
from app.platform.llm.fake import (
    FakeEmbeddingProvider,
    FakeLLMProvider,
    FakeRerankProvider,
)


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


class TestProtocolConformance:
    def test_fakes_satisfy_protocols(self) -> None:
        assert isinstance(FakeLLMProvider(), LLMProvider)
        assert isinstance(FakeEmbeddingProvider(), EmbeddingProvider)
        assert isinstance(FakeRerankProvider(), RerankProvider)


class TestFakeEmbedding:
    @pytest.fixture
    def provider(self) -> FakeEmbeddingProvider:
        return FakeEmbeddingProvider(dimension=256)

    async def test_shape_and_normalization(self, provider: FakeEmbeddingProvider) -> None:
        vectors = await provider.embed(["液压泵压力异常"], "document")
        assert len(vectors) == 1
        assert len(vectors[0]) == 256
        assert math.isclose(math.sqrt(sum(v * v for v in vectors[0])), 1.0, rel_tol=1e-6)

    async def test_deterministic(self, provider: FakeEmbeddingProvider) -> None:
        first = await provider.embed(["同一段文本"], "document")
        second = await provider.embed(["同一段文本"], "document")
        assert first == second

    async def test_similar_text_scores_higher(self, provider: FakeEmbeddingProvider) -> None:
        vectors = await provider.embed(
            ["液压泵压力异常处理", "液压泵压力异常排查", "会议室预订流程"], "document"
        )
        near = _cosine(vectors[0], vectors[1])
        far = _cosine(vectors[0], vectors[2])
        # 没有这条性质，用 Fake 测检索排序就毫无意义
        assert near > far

    async def test_empty_input(self, provider: FakeEmbeddingProvider) -> None:
        assert await provider.embed([], "query") == []


class TestFakeLLM:
    async def test_chat_reports_usage(self) -> None:
        result = await FakeLLMProvider().chat([Message(role="user", content="泵的额定压力")])
        assert result.usage.prompt_tokens > 0
        assert result.usage.total_tokens == (
            result.usage.prompt_tokens + result.usage.completion_tokens
        )

    async def test_stream_reassembles_to_chat_output(self) -> None:
        provider = FakeLLMProvider()
        messages = [Message(role="user", content="泵的额定压力")]
        expected = (await provider.chat(messages)).content

        chunks: list[str] = []
        usage = None
        async for delta in provider.stream(messages):
            chunks.append(delta.content)
            if delta.usage:
                usage = delta.usage

        assert "".join(chunks) == expected
        # 用量只在末帧给出，计费逻辑依赖这个约定
        assert usage is not None and usage.total_tokens > 0


class TestFakeRerank:
    async def test_orders_by_overlap(self) -> None:
        docs = ["液压泵维护周期为 500 小时", "空调滤网更换说明", "液压泵压力检查步骤"]
        results = await FakeRerankProvider().rerank("液压泵压力", docs, top_n=2)
        assert len(results) == 2
        assert results[0].index == 2
        assert results[0].score >= results[1].score

    async def test_empty_docs(self) -> None:
        assert await FakeRerankProvider().rerank("任意", [], top_n=5) == []
