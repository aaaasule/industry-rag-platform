"""identity 的数据访问。

仓储层只做查询与持久化，不做鉴权判断——那属于 service 层。这样切分之后，
"某个查询是否漏了权限过滤"只需要审查 service，不必逐条读 SQL。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.modules.identity.models import ROLE_OWNER, Membership, Tenant, User
from app.platform.db import set_rls_context


class IdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bind_user_context(self, user_id: uuid.UUID) -> None:
        """登录时租户尚未确定，先声明用户身份，memberships 的 RLS 才放行。

        见 0001 迁移里的双键策略：没有这一步，"我能进哪些租户"查不出任何行。
        """
        await set_rls_context(self._session, user_id=user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_user(self, user_id: uuid.UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_tenant(self, tenant_id: uuid.UUID) -> Tenant | None:
        return await self._session.get(Tenant, tenant_id)

    async def list_memberships(self, user_id: uuid.UUID) -> list[Membership]:
        """按 id 排序即按加入时间排序（UUID v7 时间有序）。"""
        stmt = (
            select(Membership)
            .options(joinedload(Membership.tenant))
            .where(Membership.user_id == user_id)
            .order_by(Membership.id)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_membership(self, user_id: uuid.UUID, tenant_id: uuid.UUID) -> Membership | None:
        stmt = (
            select(Membership)
            .options(joinedload(Membership.tenant), joinedload(Membership.user))
            .where(Membership.user_id == user_id, Membership.tenant_id == tenant_id)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list_tenant_memberships(self, tenant_id: uuid.UUID) -> list[Membership]:
        """当前租户全部成员（含用户信息），按加入时间升序。"""
        stmt = (
            select(Membership)
            .options(joinedload(Membership.user))
            .where(Membership.tenant_id == tenant_id)
            .order_by(Membership.created_at.asc(), Membership.id.asc())
        )
        return list((await self._session.execute(stmt)).scalars().unique().all())

    async def count_owners(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Membership)
            .where(Membership.tenant_id == tenant_id, Membership.role == ROLE_OWNER)
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def add_user(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    async def add_membership(self, membership: Membership) -> Membership:
        self._session.add(membership)
        await self._session.flush()
        return membership

    async def delete_membership(self, membership: Membership) -> None:
        await self._session.delete(membership)
        await self._session.flush()

    async def touch_last_login(self, user: User) -> None:
        user.last_login_at = datetime.now(UTC)
        await self._session.flush()

    async def update_password_hash(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        await self._session.flush()
