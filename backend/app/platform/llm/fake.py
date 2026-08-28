"""Fake Provider：确定性、零网络，用于单元测试与本地开发。

刻意不做成"返回固定字符串"的哑实现。FakeEmbedding 用字符 n-gram 散列成向量，
相似文本得到相近向量，因此检索链路的排序逻辑在没有真实模型时也能被测出对错。
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import re
from collections.abc import AsyncIterator
from typing import Any

from app.platform.llm.base import (
    ChatResult,
    Delta,
    InputType,
    Message,
    ScoredIndex,
    Usage,
    Vector,
)

_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+")


def _tokenize(text: str) -> list[str]:
    """中文按字、西文按词。粗糙但对 Fake 足够，且与全文检索的直觉一致。"""
    return _TOKEN_RE.findall(text.lower())


def _estimate_tokens(text: str) -> int:
    """粗略估算：中文 1 字≈1 token，西文 4 字符≈1 token。"""
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    return cjk + max(1, (len(text) - cjk) // 4)


class FakeEmbeddingProvider:
    name = "fake"

    def __init__(self, dimension: int = 1024) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: list[str], input_type: InputType) -> list[Vector]:
        return [self._embed_one(t, input_type) for t in texts]

    def _embed_one(self, text: str, input_type: InputType) -> Vector:
        vec = [0.0] * self._dimension
        tokens = _tokenize(text)
        for token in tokens:
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            slot = int.from_bytes(digest[:4], "big") % self._dimension
            sign = 1.0 if digest[4] & 1 else -1.0
            vec[slot] += sign
        # query / document 加一点固定偏移，模拟非对称编码模型的行为差异
        bias_slot = 0 if input_type == "query" else 1
        vec[bias_slot] += 0.5

        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class FakeLLMProvider:
    name = "fake"

    def __init__(self, model: str = "fake-chat", latency_ms: int = 0) -> None:
        self.model = model
        self._latency_ms = latency_ms

    async def chat(self, messages: list[Message], **opts: Any) -> ChatResult:
        if self._latency_ms:
            await asyncio.sleep(self._latency_ms / 1000)
        content = self._compose(messages)
        prompt_tokens = sum(_estimate_tokens(m.content) for m in messages)
        return ChatResult(
            content=content,
            usage=Usage(prompt_tokens=prompt_tokens, completion_tokens=_estimate_tokens(content)),
            model=self.model,
        )

    async def stream(self, messages: list[Message], **opts: Any) -> AsyncIterator[Delta]:
        result = await self.chat(messages, **opts)
        for ch in result.content:
            if self._latency_ms:
                await asyncio.sleep(self._latency_ms / 1000)
            yield Delta(content=ch)
        yield Delta(usage=result.usage, finish_reason="stop")

    @staticmethod
    def _compose(messages: list[Message]) -> str:
        system = next((m.content for m in messages if m.role == "system"), "")
        # 指代消解 / 查询扩展：返回固定可断言字符串，避免测试依赖真实改写
        if "指代" in system:
            return "HYD-2201的检修周期是多少？"
        question = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            "",
        )
        has_context = any("[1]" in m.content for m in messages if m.role == "system")
        if has_context:
            return f"根据资料，{question} 的答复如下。[1]"
        return f"（Fake）收到问题：{question}"


class FakeRerankProvider:
    name = "fake"

    async def rerank(self, query: str, docs: list[str], top_n: int) -> list[ScoredIndex]:
        """按 query token 覆盖率打分，确定性且与直觉一致。"""
        q_tokens = set(_tokenize(query))
        scored = []
        for i, doc in enumerate(docs):
            d_tokens = set(_tokenize(doc))
            overlap = len(q_tokens & d_tokens)
            score = overlap / len(q_tokens) if q_tokens else 0.0
            scored.append(ScoredIndex(index=i, score=score))
        scored.sort(key=lambda s: (-s.score, s.index))
        return scored[:top_n]
