"""认证相关接口（03 文档 §3.1）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.modules.identity.repository import IdentityRepository
from app.modules.identity.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    SessionInfo,
    SwitchTenantRequest,
    TokenPair,
    UpdateProfileRequest,
)
from app.modules.identity.service import IdentityService
from app.platform.deps import ClaimsDep, SessionDep

router = APIRouter(prefix="/auth", tags=["auth"])


def _service(session: SessionDep) -> IdentityService:
    return IdentityService(IdentityRepository(session))


ServiceDep = Depends(_service)


def _client_ip(request: Request) -> str | None:
    if request.client is None:
        return None
    return request.client.host


@router.post("/login", response_model=TokenPair, summary="口令登录")
async def login(
    payload: LoginRequest,
    request: Request,
    service: IdentityService = ServiceDep,
) -> TokenPair:
    return await service.login(
        payload.email, payload.password, payload.tenant_slug, ip=_client_ip(request)
    )


@router.post("/refresh", response_model=TokenPair, summary="刷新访问令牌")
async def refresh(payload: RefreshRequest, service: IdentityService = ServiceDep) -> TokenPair:
    return await service.refresh(payload.refresh_token)


@router.post("/switch-tenant", response_model=TokenPair, summary="切换当前租户")
async def switch_tenant(
    payload: SwitchTenantRequest,
    claims: ClaimsDep,
    request: Request,
    service: IdentityService = ServiceDep,
) -> TokenPair:
    return await service.switch_tenant(claims, payload.tenant_id, ip=_client_ip(request))


@router.get("/me", response_model=SessionInfo, summary="当前会话信息")
async def me(claims: ClaimsDep, service: IdentityService = ServiceDep) -> SessionInfo:
    return await service.session_info(claims)


@router.patch("/me", response_model=SessionInfo, summary="更新个人资料")
async def update_me(
    payload: UpdateProfileRequest,
    claims: ClaimsDep,
    service: IdentityService = ServiceDep,
) -> SessionInfo:
    return await service.update_profile(claims, payload.display_name)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="修改密码",
)
async def change_password(
    payload: ChangePasswordRequest,
    claims: ClaimsDep,
    service: IdentityService = ServiceDep,
) -> None:
    await service.change_password(claims, payload.current_password, payload.new_password)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="登出")
async def logout(claims: ClaimsDep) -> None:
    """M0 用无状态 JWT，登出由前端清除本地令牌完成。

    引入令牌吊销名单（Redis 存 jti 黑名单至过期）留到后续——
    在只有内网试点用户的阶段，为它引入一次额外的 Redis 往返不划算。
    """
    return None
