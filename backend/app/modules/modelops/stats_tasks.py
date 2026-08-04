"""用量 stats 队列任务。"""

from __future__ import annotations

import asyncio
from typing import Any

from app.modules.modelops.usage_flush import aggregate_hourlies, flush_usage_buffer
from app.worker import celery_app


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


@celery_app.task(name="stats.flush_usages", queue="stats")
def flush_usages() -> int:
    return int(_run(flush_usage_buffer()))


@celery_app.task(name="stats.aggregate_hourlies", queue="stats")
def aggregate_hourlies_task(lookback_hours: int = 48) -> int:
    return int(_run(aggregate_hourlies(lookback_hours=lookback_hours)))
