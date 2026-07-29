"""模型接入点 HTTP 接口。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.modules.identity.models import ROLE_ADMIN
from app.modules.modelops.repository import ModelConnectionRepository
from app.modules.modelops.schemas import (
    ConnectionTestResult,
    CredentialUpdate,
    ModelConnectionCreate,
    ModelConnectionOut,
    ModelConnectionUpdate,
    RoutesOut,
)
from app.modules.modelops.service import ModelOpsService
from app.platform.deps import ClaimsDep, SettingsDep, TenantSessionDep, require_role

router = APIRouter(prefix="/model-connections", tags=["modelops"])


def _service(session: TenantSessionDep, settings: SettingsDep) -> ModelOpsService:
    return ModelOpsService(ModelConnectionRepository(session), settings)


ServiceDep = Depends(_service)


@router.get(
    "",
    response_model=list[ModelConnectionOut],
    summary="列出接入点",
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def list_connections(
    claims: ClaimsDep,
    service: ModelOpsService = ServiceDep,
) -> list[ModelConnectionOut]:
    return await service.list_connections(claims)


@router.get(
    "/routes",
    response_model=RoutesOut,
    summary="各用途当前命中接入点",
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def list_routes(claims: ClaimsDep, service: ModelOpsService = ServiceDep) -> RoutesOut:
    return await service.routes(claims)


@router.post(
    "",
    response_model=ModelConnectionOut,
    status_code=201,
    summary="新建租户接入点",
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def create_connection(
    payload: ModelConnectionCreate,
    claims: ClaimsDep,
    service: ModelOpsService = ServiceDep,
) -> ModelConnectionOut:
    return await service.create(claims, payload)


@router.patch(
    "/{connection_id}",
    response_model=ModelConnectionOut,
    summary="更新接入点",
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def update_connection(
    connection_id: uuid.UUID,
    payload: ModelConnectionUpdate,
    claims: ClaimsDep,
    service: ModelOpsService = ServiceDep,
) -> ModelConnectionOut:
    return await service.update(claims, connection_id, payload)


@router.put(
    "/{connection_id}/credential",
    response_model=ModelConnectionOut,
    summary="更新凭证（只写不读）",
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def update_credential(
    connection_id: uuid.UUID,
    payload: CredentialUpdate,
    claims: ClaimsDep,
    service: ModelOpsService = ServiceDep,
) -> ModelConnectionOut:
    return await service.update_credential(claims, connection_id, payload)


@router.post(
    "/{connection_id}/test",
    response_model=ConnectionTestResult,
    summary="连通性探测",
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def test_connection(
    connection_id: uuid.UUID,
    claims: ClaimsDep,
    service: ModelOpsService = ServiceDep,
) -> ConnectionTestResult:
    return await service.test(claims, connection_id)


@router.delete(
    "/{connection_id}",
    status_code=204,
    summary="删除租户接入点",
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def delete_connection(
    connection_id: uuid.UUID,
    claims: ClaimsDep,
    service: ModelOpsService = ServiceDep,
) -> None:
    await service.delete(claims, connection_id)
