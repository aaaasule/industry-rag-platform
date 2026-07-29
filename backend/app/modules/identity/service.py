"""认证与租户上下文的业务逻辑。

两条不可动摇的规则：
1. 租户上下文只能来自服务端签发的 token，绝不接受客户端传入的 tenant 参数。
2. 登录失败一律返回同一个错误，不区分"用户不存在"与"口令错误"，避免账号枚举。
"""

from __future__ import annotations

import uuid

from app.modules.audit.service import AuditService
from app.modules.identity.models import Membership, Tenant, User
from app.modules.identity.permissions import PERM_READ
from app.modules.identity.permissions import visible_kb_ids as compute_visible_kb_ids
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.schemas import (
    SessionInfo,
    TenantBrief,
    TokenPair,
    UserProfile,
)
from app.platform.db import set_rls_context
from app.platform.errors import Forbidden, Unauthenticated
from app.platform.logging import get_logger
from app.platform.security import (
    TokenClaims,
    create_token,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)

logger = get_logger(__name__)

_LOGIN_FAILED = "邮箱或密码不正确"


class IdentityService:
    def __init__(self, repo: IdentityRepository) -> None:
        self._repo = repo

    async def login(
        self,
        email: str,
        password: str,
        tenant_slug: str | None,
        *,
        ip: str | None = None,
    ) -> TokenPair:
        user = await self._repo.get_user_by_email(email)
        if user is None or not user.password_hash:
            # 走一次假校验，让"用户不存在"与"口令错误"的耗时接近，堵住时序侧信道
            verify_password(password, _DUMMY_HASH)
            raise Unauthenticated(_LOGIN_FAILED)

        if not verify_password(password, user.password_hash):
            logger.info("login_failed", email_hash=_hash_email(email))
            raise Unauthenticated(_LOGIN_FAILED)

        if not user.is_active:
            raise Forbidden("账号已被停用")

        if needs_rehash(user.password_hash):
            await self._repo.update_password_hash(user, hash_password(password))

        await self._repo.bind_user_context(user.id)
        membership = await self._pick_membership(user, tenant_slug)
        await self._repo.touch_last_login(user)
        # 审计行受 RLS 约束，写入前切到目标租户
        await set_rls_context(
            self._repo._session, tenant_id=membership.tenant_id, user_id=user.id
        )
        await AuditService(self._repo._session).record(
            tenant_id=membership.tenant_id,
            actor_id=user.id,
            action="auth.login",
            target_type="session",
            target_id=None,
            payload={"email": user.email},
            ip=ip,
        )
        logger.info("login_succeeded", user_id=str(user.id), tenant_id=str(membership.tenant_id))
        return self._issue(user.id, membership)

    async def refresh(self, refresh_token: str) -> TokenPair:
        claims = decode_token(refresh_token, expected_type="refresh")
        user, membership = await self._load_active_context(claims.user_id, claims.tenant_id)
        # 角色可能在 token 有效期内被改过，刷新时以库为准重新签发
        return self._issue(user.id, membership)

    async def switch_tenant(
        self,
        claims: TokenClaims,
        tenant_id: uuid.UUID,
        *,
        ip: str | None = None,
    ) -> TokenPair:
        user, membership = await self._load_active_context(claims.user_id, tenant_id)
        await set_rls_context(self._repo._session, tenant_id=tenant_id, user_id=user.id)
        await AuditService(self._repo._session).record(
            tenant_id=tenant_id,
            actor_id=user.id,
            action="auth.switch_tenant",
            target_type="session",
            target_id=None,
            payload={
                "from_tenant_id": str(claims.tenant_id),
                "to_tenant_id": str(tenant_id),
            },
            ip=ip,
        )
        logger.info("tenant_switched", user_id=str(user.id), tenant_id=str(tenant_id))
        return self._issue(user.id, membership)

    async def session_info(self, claims: TokenClaims) -> SessionInfo:
        user, current = await self._load_active_context(claims.user_id, claims.tenant_id)
        memberships = await self._repo.list_memberships(user.id)
        return SessionInfo(
            user=UserProfile.model_validate(user),
            current_tenant=_brief(current),
            tenants=[_brief(m) for m in memberships if m.tenant.is_active],
        )

    async def visible_kb_ids(
        self, claims: TokenClaims, permission: str = PERM_READ
    ) -> list[uuid.UUID]:
        return await compute_visible_kb_ids(
            self._repo._session,
            tenant_id=claims.tenant_id,
            user_id=claims.user_id,
            role=claims.role,
            permission=permission,
        )

    async def _pick_membership(self, user: User, tenant_slug: str | None) -> Membership:
        memberships = await self._repo.list_memberships(user.id)
        active = [m for m in memberships if m.tenant.is_active]
        if not active:
            raise Forbidden("账号未加入任何可用租户")

        if tenant_slug is None:
            return active[0]

        for m in active:
            if m.tenant.slug == tenant_slug:
                return m
        raise Forbidden("无权访问该租户")

    async def _load_active_context(
        self, user_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> tuple[User, Membership]:
        user = await self._repo.get_user(user_id)
        if user is None or not user.is_active:
            raise Unauthenticated("账号不可用")

        await self._repo.bind_user_context(user_id)
        membership = await self._repo.get_membership(user_id, tenant_id)
        if membership is None:
            raise Forbidden("无权访问该租户")
        if not membership.tenant.is_active:
            raise Forbidden("租户已停用")
        return user, membership

    @staticmethod
    def _issue(user_id: uuid.UUID, membership: Membership) -> TokenPair:
        access, expires_at = create_token(
            user_id=user_id,
            tenant_id=membership.tenant_id,
            role=membership.role,
            token_type="access",
        )
        refresh, _ = create_token(
            user_id=user_id,
            tenant_id=membership.tenant_id,
            role=membership.role,
            token_type="refresh",
        )
        return TokenPair(access_token=access, refresh_token=refresh, expires_at=expires_at)


def _brief(membership: Membership) -> TenantBrief:
    tenant: Tenant = membership.tenant
    return TenantBrief(id=tenant.id, slug=tenant.slug, name=tenant.name, role=membership.role)


def _hash_email(email: str) -> str:
    """日志里不留明文邮箱，但保留可关联性。"""
    import hashlib

    return hashlib.blake2b(email.lower().encode(), digest_size=8).hexdigest()


# 固定的合法 Argon2 哈希，仅用于恒定时间的假校验
_DUMMY_HASH = hash_password("dummy-password-for-timing-equalization")
