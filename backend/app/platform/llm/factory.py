"""从 ModelConnection 或 Settings 构造 Provider。"""

from __future__ import annotations

from typing import Any

from app.modules.modelops.credentials import decrypt_credential
from app.modules.modelops.models import (
    PROVIDER_FAKE,
    ModelConnection,
)
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


def _timeout(conn: ModelConnection, settings: Settings) -> int:
    extra: dict[str, Any] = conn.extra or {}
    raw = extra.get("timeout_seconds")
    if isinstance(raw, int) and raw > 0:
        return raw
    return settings.llm_timeout_seconds


def build_llm_from_connection(
    conn: ModelConnection, *, settings: Settings | None = None
) -> LLMProvider:
    settings = settings or get_settings()
    if conn.provider_type == PROVIDER_FAKE:
        return FakeLLMProvider(model=conn.model)
    api_key = decrypt_credential(conn.credential_cipher, settings)
    return OpenAICompatibleLLM(
        _shared_client(
            base_url=conn.base_url,
            api_key=api_key,
            timeout_seconds=_timeout(conn, settings),
        ),
        conn.model,
    )


def build_embedding_from_connection(
    conn: ModelConnection, *, settings: Settings | None = None
) -> EmbeddingProvider:
    settings = settings or get_settings()
    if conn.provider_type == PROVIDER_FAKE:
        return FakeEmbeddingProvider(dimension=settings.embedding_dim)
    api_key = decrypt_credential(conn.credential_cipher, settings)
    extra = conn.extra or {}
    dim = int(extra.get("embedding_dim") or settings.embedding_dim)
    batch = int(extra.get("batch_size") or settings.embedding_batch_size)
    return OpenAICompatibleEmbedding(
        _shared_client(
            base_url=conn.base_url,
            api_key=api_key,
            timeout_seconds=_timeout(conn, settings),
        ),
        conn.model,
        dim,
        batch_size=batch,
    )


def build_rerank_from_connection(
    conn: ModelConnection, *, settings: Settings | None = None
) -> RerankProvider:
    settings = settings or get_settings()
    if conn.provider_type == PROVIDER_FAKE:
        return FakeRerankProvider()
    api_key = decrypt_credential(conn.credential_cipher, settings)
    extra = conn.extra or {}
    path = str(extra.get("rerank_path") or settings.rerank_path)
    return OpenAICompatibleRerank(
        _shared_client(
            base_url=conn.base_url,
            api_key=api_key,
            timeout_seconds=_timeout(conn, settings),
        ),
        conn.model,
        path=path,
    )


async def close_providers(settings: Settings | None = None) -> None:
    del settings  # 保留签名兼容
    for client in list(_clients.values()):
        await client.aclose()
    _clients.clear()
