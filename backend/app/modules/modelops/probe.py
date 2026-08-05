"""接入点连通性探测（手动 /test 与定时任务共用）。"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from app.modules.modelops.models import ModelConnection
from app.platform.config import Settings, get_settings
from app.platform.llm.base import Message
from app.platform.llm.factory import (
    aclose_provider,
    build_embedding_from_connection,
    build_llm_from_connection,
    build_rerank_from_connection,
)


@dataclass(frozen=True, slots=True)
class ProbeResult:
    ok: bool
    latency_ms: float
    error_message: str | None = None


async def probe_connection(
    row: ModelConnection, *, settings: Settings | None = None
) -> ProbeResult:
    """按 purposes[0] 做最小实调；异常视为失败，不抛出。"""
    cfg = settings or get_settings()
    purpose = row.purposes[0] if row.purposes else "chat"
    t0 = time.perf_counter()
    provider: Any = None
    try:
        # Celery probe 经 asyncio.run；禁止复用跨 loop 的 httpx 客户端
        if purpose == "embedding":
            provider = build_embedding_from_connection(row, settings=cfg, shared_client=False)
            await provider.embed(["ping"], input_type="query")
        elif purpose == "rerank":
            provider = build_rerank_from_connection(row, settings=cfg, shared_client=False)
            await provider.rerank("q", ["d1"], top_n=1)
        else:
            provider = build_llm_from_connection(row, settings=cfg, shared_client=False)
            await provider.chat([Message(role="user", content="ping")], max_tokens=8)
        return ProbeResult(ok=True, latency_ms=(time.perf_counter() - t0) * 1000)
    except Exception as exc:
        return ProbeResult(
            ok=False,
            latency_ms=(time.perf_counter() - t0) * 1000,
            error_message=str(exc)[:200],
        )
    finally:
        if provider is not None:
            await aclose_provider(provider)
