"""定时健康探测任务。"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.modules.modelops.models import HEALTH_DOWN, HEALTH_HEALTHY, ModelConnection
from app.modules.modelops.probe import probe_connection
from app.modules.modelops.provider_factory import clear_provider_cache
from app.platform.config import get_settings
from app.platform.logging import get_logger
from app.worker import celery_app

logger = get_logger(__name__)


async def probe_all_connections() -> dict[str, int]:
    """探测所有 enabled 接入点并写 health；返回计数。"""
    settings = get_settings()
    url = settings.database_migration_url or settings.database_url
    engine = create_async_engine(url, pool_pre_ping=True, poolclass=NullPool)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    probed = healthy = down = 0
    try:
        async with maker() as session:
            rows = list(
                (
                    await session.execute(
                        select(ModelConnection).where(ModelConnection.enabled.is_(True))
                    )
                )
                .scalars()
                .all()
            )
            for row in rows:
                result = await probe_connection(row, settings=settings)
                row.health_checked_at = datetime.now(UTC)
                if result.ok:
                    row.health = HEALTH_HEALTHY
                    healthy += 1
                else:
                    row.health = HEALTH_DOWN
                    down += 1
                    logger.warning(
                        "connection_probe_failed",
                        connection_id=str(row.id),
                        name=row.name,
                        error=result.error_message,
                    )
                probed += 1
            await session.commit()
    finally:
        await engine.dispose()

    clear_provider_cache()
    logger.info("connections_probed", probed=probed, healthy=healthy, down=down)
    return {"probed": probed, "healthy": healthy, "down": down}


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


@celery_app.task(name="modelops.probe_connections", queue="stats")
def probe_connections_task() -> dict[str, int]:
    return dict(_run(probe_all_connections()))
