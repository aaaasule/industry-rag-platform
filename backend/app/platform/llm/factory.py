"""Provider 装配。

M0 阶段从全局配置构造；M4 引入 modelops 后，改为按 ModelConnection 构造，
业务侧的调用点不需要变——这正是抽象层存在的意义。
"""

from __future__ import annotations

from functools import lru_cache

from app.platform.config import Settings, get_settings
from app.platform.llm.base import EmbeddingProvider, LLMProvider, RerankProvider
from app.platform.llm.fake import FakeEmbeddingProvider, FakeLLMProvider, FakeRerankProvider
from app.platform.llm.openai_compatible import (
    OpenAICompatibleClient,
    OpenAICompatibleEmbedding,
    OpenAICompatibleLLM,
    OpenAICompatibleRerank,
)


@lru_cache
def _client(settings: Settings) -> OpenAICompatibleClient:
    return OpenAICompatibleClient(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        timeout_seconds=settings.llm_timeout_seconds,
    )


def build_llm_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    if settings.llm_provider == "fake":
        return FakeLLMProvider(model=settings.llm_model)
    return OpenAICompatibleLLM(_client(settings), settings.llm_model)


def build_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    settings = settings or get_settings()
    if settings.embedding_provider == "fake":
        return FakeEmbeddingProvider(dimension=settings.embedding_dim)
    return OpenAICompatibleEmbedding(
        _client(settings), settings.embedding_model, settings.embedding_dim
    )


def build_rerank_provider(settings: Settings | None = None) -> RerankProvider:
    settings = settings or get_settings()
    if settings.llm_provider == "fake":
        return FakeRerankProvider()
    return OpenAICompatibleRerank(_client(settings), settings.llm_model)


async def close_providers(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if settings.llm_provider != "fake":
        await _client(settings).aclose()
