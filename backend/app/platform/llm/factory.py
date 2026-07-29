"""Provider 装配。

M0 阶段从全局配置构造；M4 引入 modelops 后，改为按 ModelConnection 构造，
业务侧的调用点不需要变——这正是抽象层存在的意义。
"""

from __future__ import annotations

from app.platform.config import Settings, get_settings
from app.platform.llm.base import EmbeddingProvider, LLMProvider, RerankProvider
from app.platform.llm.fake import FakeEmbeddingProvider, FakeLLMProvider, FakeRerankProvider
from app.platform.llm.openai_compatible import (
    OpenAICompatibleClient,
    OpenAICompatibleEmbedding,
    OpenAICompatibleLLM,
    OpenAICompatibleRerank,
)

_clients: dict[tuple[str, str, int], OpenAICompatibleClient] = {}


def _shared_client(*, base_url: str, api_key: str, timeout_seconds: int) -> OpenAICompatibleClient:
    key = (base_url, api_key, timeout_seconds)
    client = _clients.get(key)
    if client is None:
        client = OpenAICompatibleClient(
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )
        _clients[key] = client
    return client


def build_llm_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    if settings.llm_provider == "fake":
        return FakeLLMProvider(model=settings.llm_model)
    return OpenAICompatibleLLM(
        _shared_client(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key.get_secret_value(),
            timeout_seconds=settings.llm_timeout_seconds,
        ),
        settings.llm_model,
    )


def build_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    settings = settings or get_settings()
    if settings.embedding_provider == "fake":
        return FakeEmbeddingProvider(dimension=settings.embedding_dim)
    return OpenAICompatibleEmbedding(
        _shared_client(
            base_url=settings.resolved_embedding_base_url,
            api_key=settings.resolved_embedding_api_key,
            timeout_seconds=settings.llm_timeout_seconds,
        ),
        settings.embedding_model,
        settings.embedding_dim,
        batch_size=settings.embedding_batch_size,
    )


def build_rerank_provider(settings: Settings | None = None) -> RerankProvider:
    settings = settings or get_settings()
    if settings.resolved_rerank_provider == "fake":
        return FakeRerankProvider()
    return OpenAICompatibleRerank(
        _shared_client(
            base_url=settings.resolved_rerank_base_url,
            api_key=settings.resolved_rerank_api_key,
            timeout_seconds=settings.llm_timeout_seconds,
        ),
        settings.rerank_model,
        path=settings.rerank_path,
    )


async def close_providers(settings: Settings | None = None) -> None:
    del settings  # 关闭进程内全部共享 client
    for client in list(_clients.values()):
        await client.aclose()
    _clients.clear()
