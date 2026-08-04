"""model_connections 数据访问。"""

from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.modelops.models import ModelConnection


class ModelConnectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_visible(self, tenant_id: uuid.UUID) -> list[ModelConnection]:
        stmt = (
            select(ModelConnection)
            .where(
                or_(
                    ModelConnection.tenant_id == tenant_id,
                    ModelConnection.tenant_id.is_(None),
                )
            )
            .order_by(ModelConnection.priority.asc(), ModelConnection.id.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get(self, connection_id: uuid.UUID) -> ModelConnection | None:
        return await self._session.get(ModelConnection, connection_id)

    async def list_for_purpose(
        self, *, tenant_id: uuid.UUID, purpose: str
    ) -> list[ModelConnection]:
        """租户点在前、平台点在后；同层按 priority。"""
        stmt = (
            select(ModelConnection)
            .where(
                ModelConnection.enabled.is_(True),
                ModelConnection.purposes.contains([purpose]),
                or_(
                    ModelConnection.tenant_id == tenant_id,
                    ModelConnection.tenant_id.is_(None),
                ),
            )
            .order_by(
                # NULLS LAST：租户非空排前（Postgres：NULL 在 ASC 默认 LAST）
                ModelConnection.tenant_id.asc().nulls_last(),
                ModelConnection.priority.asc(),
                ModelConnection.id.asc(),
            )
        )
        rows = list((await self._session.execute(stmt)).scalars().all())
        # 确保租户优先：nulls_last 已让非空在前；再稳定分区
        tenant_rows = [r for r in rows if r.tenant_id == tenant_id]
        platform_rows = [r for r in rows if r.tenant_id is None]
        return tenant_rows + platform_rows

    async def add(self, row: ModelConnection) -> ModelConnection:
        self._session.add(row)
        await self._session.flush()
        return row

    async def delete(self, row: ModelConnection) -> None:
        await self._session.delete(row)
        await self._session.flush()
