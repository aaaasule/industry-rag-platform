"""Provider 抽象层——整个系统最重要的防腐层。

业务代码永远不直接 import openai / dashscope / 任何厂商 SDK。换模型只改配置；
单元测试用 Fake Provider，不打网络；私有化部署实现一个本地 Provider 即可，
业务代码零改动。（01 文档 §4.1、ADR-002）

这一层只负责"怎么调用"。"调用谁、通不通、花多少钱"属于 modelops 模块，
不要把配置查询和用量写库塞进 Provider 实现里，那会让它无法被单测。
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

Role = Literal["system", "user", "assistant"]
InputType = Literal["query", "document"]

Vector = list[float]


@dataclass(frozen=True, slots=True)
class Message:
    role: Role
    content: str


@dataclass(frozen=True, slots=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True, slots=True)
class ChatResult:
    content: str
    usage: Usage
    model: str
    finish_reason: str = "stop"
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Delta:
    """流式增量。usage 只在最后一帧（content 为空）出现。"""

    content: str = ""
    usage: Usage | None = None
    finish_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ScoredIndex:
    index: int
    score: float


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    async def chat(self, messages: list[Message], **opts: Any) -> ChatResult: ...

    def stream(self, messages: list[Message], **opts: Any) -> AsyncIterator[Delta]: ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    name: str

    async def embed(self, texts: list[str], input_type: InputType) -> list[Vector]: ...

    @property
    def dimension(self) -> int: ...


@runtime_checkable
class RerankProvider(Protocol):
    name: str

    async def rerank(self, query: str, docs: list[str], top_n: int) -> list[ScoredIndex]: ...
