"""httpx 客户端生命周期：Celery asyncio.run 边界不可跨任务复用。"""

from __future__ import annotations

import asyncio
import json

import httpx

from app.platform.llm.factory import _get_client, aclose_provider
from app.platform.llm.openai_compatible import OpenAICompatibleClient, OpenAICompatibleEmbedding


def _embedding_response(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content.decode())
    n = len(body["input"]) if isinstance(body.get("input"), list) else 1
    return httpx.Response(
        200,
        json={
            "data": [{"index": i, "embedding": [0.1, 0.2, 0.3, 0.4]} for i in range(n)],
            "model": "mock",
        },
    )


def test_get_client_shared_reuses_instance() -> None:
    a = _get_client(base_url="http://a", api_key="k", timeout_seconds=10, shared=True)
    b = _get_client(base_url="http://a", api_key="k", timeout_seconds=10, shared=True)
    assert a is b


def test_get_client_unshared_are_distinct() -> None:
    a = _get_client(base_url="http://b", api_key="k", timeout_seconds=10, shared=False)
    b = _get_client(base_url="http://b", api_key="k", timeout_seconds=10, shared=False)
    assert a is not b


def test_unshared_embedding_survives_two_asyncio_runs() -> None:
    """模拟 Celery 两次 asyncio.run：每次新建 + aclose，不应 Event loop is closed。"""

    async def once() -> None:
        transport = httpx.MockTransport(_embedding_response)
        http = httpx.AsyncClient(transport=transport)
        client = OpenAICompatibleClient(
            base_url="http://test/v1",
            api_key="k",
            client=http,
        )
        emb = OpenAICompatibleEmbedding(client, "mock", 4, batch_size=8)
        try:
            vectors = await emb.embed(["hello"], input_type="document")
            assert len(vectors) == 1
            assert len(vectors[0]) == 4
        finally:
            await aclose_provider(emb)

    asyncio.run(once())
    asyncio.run(once())


def test_aclose_provider_noop_for_fake_like_object() -> None:
    async def run() -> None:
        await aclose_provider(object())

    asyncio.run(run())
