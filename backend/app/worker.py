"""Celery 应用。

按 05 文档拆三个队列：ingest（解析/OCR，CPU 密集）、embed（向量化，受限于
上游 API 速率）、stats（用量预聚合，定时）。分开的理由是它们的失败模式、
重试策略和扩容维度都不同，混在一个队列里会互相拖累。
"""

from __future__ import annotations

from celery import Celery

from app.platform.config import get_settings
from app.platform.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level, settings.log_format)

celery_app = Celery("irp", broker=settings.redis_url, backend=settings.redis_url)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    # 解析任务耗时长且不幂等成本高，禁止预取多个任务堆在一个 worker 上
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    task_default_queue="ingest",
    task_queues={
        "ingest": {"exchange": "ingest", "routing_key": "ingest"},
        "embed": {"exchange": "embed", "routing_key": "embed"},
        "stats": {"exchange": "stats", "routing_key": "stats"},
    },
    result_expires=3600,
)

# 须在 celery_app 配置之后导入；autodiscover(["app.modules"]) 只会找 *.tasks
import app.modules.ingestion.tasks  # noqa: E402
import app.modules.modelops.health_tasks  # noqa: E402
import app.modules.modelops.stats_tasks  # noqa: E402, F401

celery_app.autodiscover_tasks(["app.modules.ingestion"], related_name="tasks")

celery_app.conf.beat_schedule = {
    "flush-usages-every-minute": {
        "task": "stats.flush_usages",
        "schedule": 60.0,
        "options": {"queue": "stats"},
    },
    "aggregate-hourlies-hourly": {
        "task": "stats.aggregate_hourlies",
        "schedule": 3600.0,
        "options": {"queue": "stats"},
    },
    "probe-connections-every-5min": {
        "task": "modelops.probe_connections",
        "schedule": 300.0,
        "options": {"queue": "stats"},
    },
}


@celery_app.task(name="system.ping")
def ping() -> str:
    """M0 冒烟用：验证 broker 与 worker 链路通畅。"""
    return "pong"
