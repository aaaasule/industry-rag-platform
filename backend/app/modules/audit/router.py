"""管理端审计查询接口。"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.modules.audit.schemas import AuditLogList
from app.modules.audit.service import AuditService
from app.modules.identity.models import ROLE_ADMIN
from app.platform.deps import ClaimsDep, TenantSessionDep, require_role

router = APIRouter(prefix="/admin", tags=["admin"])


def _service(session: TenantSessionDep) -> AuditService:
    return AuditService(session)


ServiceDep = Depends(_service)


@router.get(
    "/audit-logs",
    response_model=AuditLogList,
    summary="查询审计日志",
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def list_audit_logs(
    claims: ClaimsDep,
    action: str | None = None,
    actor_id: uuid.UUID | None = None,
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: AuditService = ServiceDep,
) -> AuditLogList:
    return await service.list_logs(
        tenant_id=claims.tenant_id,
        action=action,
        actor_id=actor_id,
        from_time=from_time,
        to_time=to_time,
        limit=limit,
        offset=offset,
    )
