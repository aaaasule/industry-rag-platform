"""审计写入与查询。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditLogList, AuditLogOut
from app.platform.ids import uuid7
from app.platform.logging import get_logger

logger = get_logger(__name__)


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        *,
        tenant_id: uuid.UUID,
        actor_id: uuid.UUID | None,
        action: str,
        target_type: str,
        target_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
        ip: str | None = None,
    ) -> None:
        """写入一条审计；异常仅记日志，不抛出，避免拖垮主业务。"""
        try:
            async with self._session.begin_nested():
                self._session.add(
                    AuditLog(
                        id=uuid7(),
                        tenant_id=tenant_id,
                        actor_id=actor_id,
                        action=action,
                        target_type=target_type,
                        target_id=target_id,
                        payload=payload or {},
                        ip=ip,
                    )
                )
                await self._session.flush()
        except Exception as exc:
            logger.warning(
                "audit_record_failed",
                action=action,
                tenant_id=str(tenant_id),
                error=str(exc),
            )

    async def list_logs(
        self,
        *,
        tenant_id: uuid.UUID,
        action: str | None = None,
        actor_id: uuid.UUID | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AuditLogList:
        filters = [AuditLog.tenant_id == tenant_id]
        if action is not None:
            filters.append(AuditLog.action == action)
        if actor_id is not None:
            filters.append(AuditLog.actor_id == actor_id)
        if from_time is not None:
            filters.append(AuditLog.created_at >= from_time)
        if to_time is not None:
            filters.append(AuditLog.created_at < to_time)

        total = (
            await self._session.execute(select(func.count()).select_from(AuditLog).where(*filters))
        ).scalar_one()

        stmt = (
            select(AuditLog)
            .where(*filters)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        return AuditLogList(
            items=[AuditLogOut.model_validate(r) for r in rows],
            total=int(total),
        )
