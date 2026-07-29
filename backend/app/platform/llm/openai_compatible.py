"""OpenAI 兼容接口的 Provider 实现。

覆盖 OpenAI / DeepSeek / 通义 / vLLM / Ollama 等绝大多数国内外端点——它们都
兼容 `/chat/completions` 与 `/embeddings`。因此"换厂商"在多数情况下只是换
base_url 和 api_key，不需要新写 Provider。
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.platform.errors import ProviderUnavailable
from app.platform.llm.base import (
    ChatResult,
    Delta,
    InputType,
    Message,
    ScoredIndex,
    Usage,
    Vector,
)
from app.platform.logging import get_logger

logger = get_logger(__name__)

_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class OpenAICompatibleClient:
    """共享的 HTTP 调用与错误归一化。"""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: int = 60,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        self._timeout = timeout_seconds
        self._client = client

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            resp = await self._ensure_client().post(
                f"{self._base_url}{path}", json=payload, headers=self._headers
            )
        except httpx.HTTPError as exc:
            raise ProviderUnavailable(f"上游请求失败：{exc.__class__.__name__}") from exc

        if resp.status_code in _RETRYABLE_STATUS:
            raise ProviderUnavailable(f"上游返回 {resp.status_code}，建议重试")
        if resp.status_code >= 400:
            logger.warning("provider_error", status=resp.status_code, path=path)
            raise ProviderUnavailable(f"上游返回 {resp.status_code}")
        return resp.json()

    def stream_lines(self, path: str, payload: dict[str, Any]) -> Any:
        return self._ensure_client().stream(
            "POST", f"{self._base_url}{path}", json=payload, headers=self._headers
        )


class OpenAICompatibleLLM:
    name = "openai_compatible"

    def __init__(self, client: OpenAICompatibleClient, model: str) -> None:
        self._client = client
        self.model = model

    async def chat(self, messages: list[Message], **opts: Any) -> ChatResult:
        payload = self._payload(messages, stream=False, **opts)
        data = await self._client.post("/chat/completions", payload)
        choice = data["choices"][0]
        return ChatResult(
            content=choice["message"]["content"] or "",
            usage=_parse_usage(data.get("usage")),
            model=data.get("model", self.model),
            finish_reason=choice.get("finish_reason") or "stop",
        )

    async def stream(self, messages: list[Message], **opts: Any) -> AsyncIterator[Delta]:
        payload = self._payload(messages, stream=True, **opts)
        payload["stream_options"] = {"include_usage": True}

        async with self._client.stream_lines("/chat/completions", payload) as resp:
            if resp.status_code >= 400:
                await resp.aread()
                raise ProviderUnavailable(f"上游返回 {resp.status_code}")
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                delta = _parse_stream_chunk(chunk)
                if delta is not None:
                    yield delta

    def _payload(self, messages: list[Message], *, stream: bool, **opts: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": opts.pop("model", self.model),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
        }
        for key in ("temperature", "top_p", "max_tokens", "seed", "stop"):
            if key in opts and opts[key] is not None:
                payload[key] = opts[key]
        return payload


class OpenAICompatibleEmbedding:
    name = "openai_compatible"

    def __init__(
        self,
        client: OpenAICompatibleClient,
        model: str,
        dimension: int,
        *,
        batch_size: int = 10,
    ) -> None:
        self._client = client
        self.model = model
        self._dimension = dimension
        self._batch_size = max(1, batch_size)

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: list[str], input_type: InputType) -> list[Vector]:
        del input_type  # OpenAI 兼容端点多数不区分；保留签名以兼容 Protocol
        if not texts:
            return []
        out: list[Vector] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            payload: dict[str, Any] = {
                "model": self.model,
                "input": batch,
                "encoding_format": "float",
                "dimensions": self._dimension,
            }
            data = await self._client.post("/embeddings", payload)
            items = sorted(data["data"], key=lambda d: d.get("index", 0))
            out.extend(item["embedding"] for item in items)
        return out


class OpenAICompatibleRerank:
    """DashScope 兼容路径为 `/reranks`；Jina 等仍用 `/rerank`，由 path 配置。"""

    name = "openai_compatible"

    def __init__(
        self,
        client: OpenAICompatibleClient,
        model: str,
        *,
        path: str = "/reranks",
    ) -> None:
        self._client = client
        self.model = model
        self._path = path if path.startswith("/") else f"/{path}"

    async def rerank(self, query: str, docs: list[str], top_n: int) -> list[ScoredIndex]:
        if not docs:
            return []
        data = await self._client.post(
            self._path,
            {
                "model": self.model,
                "query": query,
                "documents": docs,
                "top_n": top_n,
            },
        )
        results = data.get("results") or data.get("data") or []
        scored: list[ScoredIndex] = []
        for item in results:
            idx = item.get("index")
            score = item.get("relevance_score", item.get("score"))
            if idx is None or score is None:
                continue
            scored.append(ScoredIndex(index=int(idx), score=float(score)))
        return scored


def _parse_usage(raw: dict[str, Any] | None) -> Usage:
    if not raw:
        return Usage()
    return Usage(
        prompt_tokens=raw.get("prompt_tokens", 0),
        completion_tokens=raw.get("completion_tokens", 0),
    )


def _parse_stream_chunk(chunk: str) -> Delta | None:
    try:
        data = json.loads(chunk)
    except json.JSONDecodeError:
        logger.warning("stream_chunk_unparsable", length=len(chunk))
        return None

    if data.get("usage") and not data.get("choices"):
        return Delta(usage=_parse_usage(data["usage"]), finish_reason="stop")

    choices = data.get("choices") or []
    if not choices:
        return None
    choice = choices[0]
    return Delta(
        content=choice.get("delta", {}).get("content") or "",
        finish_reason=choice.get("finish_reason"),
    )
