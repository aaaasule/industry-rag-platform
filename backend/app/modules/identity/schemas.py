"""identity 模块的请求/响应模型。"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    tenant_slug: str | None = Field(
        default=None,
        description="用户属于多个租户时指定；不传则登录到最早加入的租户",
    )


class RefreshRequest(BaseModel):
    refresh_token: str


class SwitchTenantRequest(BaseModel):
    tenant_id: uuid.UUID


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_at: datetime


class TenantBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    role: str


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    status: str


class SessionInfo(BaseModel):
    """/auth/me 的返回：当前用户 + 当前租户 + 可切换的租户列表。"""

    user: UserProfile
    current_tenant: TenantBrief
    tenants: list[TenantBrief]


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class MemberCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="member", description="member | admin | owner")
    create_if_missing: bool = Field(
        default=True,
        description="邮箱对应用户不存在时是否创建账号（无邮件邀请；返回 temporary_password）",
    )
    display_name: str | None = Field(
        default=None, min_length=1, max_length=128, description="仅新建用户时使用"
    )


class MemberRoleUpdate(BaseModel):
    role: str = Field(description="member | admin | owner")


class MemberOut(BaseModel):
    user_id: uuid.UUID
    email: str
    display_name: str
    role: str
    created_at: datetime
    created_user: bool = False
    temporary_password: str | None = None


class MembershipList(BaseModel):
    items: list[MemberOut]
