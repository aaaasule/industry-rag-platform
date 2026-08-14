"""租户成员管理接口。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.modules.identity.membership_service import MembershipService
from app.modules.identity.models import ROLE_ADMIN
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.schemas import MemberCreate, MemberOut, MemberRoleUpdate, MembershipList
from app.platform.deps import ClaimsDep, TenantSessionDep, require_role

router = APIRouter(
    prefix="/memberships",
    tags=["memberships"],
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)


def _service(session: TenantSessionDep) -> MembershipService:
    return MembershipService(IdentityRepository(session))


ServiceDep = Depends(_service)


@router.get("", response_model=MembershipList, summary="列出当前租户成员")
async def list_memberships(
    claims: ClaimsDep, service: MembershipService = ServiceDep
) -> MembershipList:
    return await service.list_members(claims)


@router.post(
    "",
    response_model=MemberOut,
    status_code=status.HTTP_201_CREATED,
    summary="按邮箱添加成员；不存在则创建账号（create_if_missing）",
)
async def add_membership(
    payload: MemberCreate,
    claims: ClaimsDep,
    service: MembershipService = ServiceDep,
) -> MemberOut:
    return await service.add_member(claims, payload)


@router.patch(
    "/{user_id}",
    response_model=MemberOut,
    summary="修改成员角色",
)
async def update_membership(
    user_id: uuid.UUID,
    payload: MemberRoleUpdate,
    claims: ClaimsDep,
    service: MembershipService = ServiceDep,
) -> MemberOut:
    return await service.update_role(claims, user_id, payload)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="移出成员",
)
async def delete_membership(
    user_id: uuid.UUID,
    claims: ClaimsDep,
    service: MembershipService = ServiceDep,
) -> None:
    await service.remove_member(claims, user_id)
