"""租户成员管理业务逻辑。"""

from __future__ import annotations

import uuid

from app.modules.audit.service import AuditService
from app.modules.identity.models import ROLE_OWNER, ROLES, Membership, role_at_least
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.schemas import MemberCreate, MemberOut, MemberRoleUpdate, MembershipList
from app.platform.errors import AppError, Conflict, Forbidden, NotFound
from app.platform.ids import uuid7
from app.platform.security import TokenClaims


class MembershipService:
    def __init__(self, repo: IdentityRepository) -> None:
        self._repo = repo
        self._audit = AuditService(repo._session)

    async def list_members(self, claims: TokenClaims) -> MembershipList:
        rows = await self._repo.list_tenant_memberships(claims.tenant_id)
        return MembershipList(items=[_member_out(m) for m in rows])

    async def add_member(self, claims: TokenClaims, payload: MemberCreate) -> MemberOut:
        role = payload.role
        if role not in ROLES:
            raise AppError(f"无效角色: {role}", code="validation_error")

        user = await self._repo.get_user_by_email(payload.email)
        if user is None:
            raise NotFound("user not found")

        if not role_at_least(claims.role, ROLE_OWNER) and role == ROLE_OWNER:
            raise Forbidden("仅 owner 可将成员设为 owner")

        existing = await self._repo.get_membership(user.id, claims.tenant_id)
        if existing is not None:
            raise Conflict("already a member")

        membership = Membership(
            id=uuid7(),
            tenant_id=claims.tenant_id,
            user_id=user.id,
            role=role,
        )
        await self._repo.add_membership(membership)
        # 回填 user 供响应（joinedload 未跑）
        membership.user = user

        await self._audit.record(
            tenant_id=claims.tenant_id,
            actor_id=claims.user_id,
            action="membership.add",
            target_type="membership",
            target_id=membership.id,
            payload={"email": user.email, "role": role, "user_id": str(user.id)},
        )
        return _member_out(membership)

    async def update_role(
        self, claims: TokenClaims, user_id: uuid.UUID, payload: MemberRoleUpdate
    ) -> MemberOut:
        new_role = payload.role
        if new_role not in ROLES:
            raise AppError(f"无效角色: {new_role}", code="validation_error")

        membership = await self._repo.get_membership(user_id, claims.tenant_id)
        if membership is None:
            raise NotFound("成员不存在")

        old_role = membership.role
        if old_role == new_role:
            return _member_out(membership)

        actor_is_owner = role_at_least(claims.role, ROLE_OWNER)
        if not actor_is_owner and (old_role == ROLE_OWNER or new_role == ROLE_OWNER):
            raise Forbidden("仅 owner 可变更涉及 owner 的角色")

        if (
            old_role == ROLE_OWNER
            and new_role != ROLE_OWNER
            and await self._repo.count_owners(claims.tenant_id) <= 1
        ):
            raise AppError("cannot demote the last owner", code="bad_request")

        membership.role = new_role
        await self._repo._session.flush()

        await self._audit.record(
            tenant_id=claims.tenant_id,
            actor_id=claims.user_id,
            action="membership.role_change",
            target_type="membership",
            target_id=membership.id,
            payload={"user_id": str(user_id), "from": old_role, "to": new_role},
        )
        return _member_out(membership)

    async def remove_member(self, claims: TokenClaims, user_id: uuid.UUID) -> None:
        if user_id == claims.user_id:
            raise AppError("cannot remove yourself", code="bad_request")

        membership = await self._repo.get_membership(user_id, claims.tenant_id)
        if membership is None:
            raise NotFound("成员不存在")

        if membership.role == ROLE_OWNER and not role_at_least(claims.role, ROLE_OWNER):
            raise Forbidden("admin 不能删除 owner")

        if (
            membership.role == ROLE_OWNER
            and await self._repo.count_owners(claims.tenant_id) <= 1
        ):
            raise AppError("cannot remove the last owner", code="bad_request")

        email = membership.user.email if membership.user else None
        role = membership.role
        membership_id = membership.id

        await self._repo.delete_membership(membership)
        await self._audit.record(
            tenant_id=claims.tenant_id,
            actor_id=claims.user_id,
            action="membership.remove",
            target_type="membership",
            target_id=membership_id,
            payload={"user_id": str(user_id), "email": email, "role": role},
        )


def _member_out(m: Membership) -> MemberOut:
    user = m.user
    return MemberOut(
        user_id=m.user_id,
        email=user.email,
        display_name=user.display_name,
        role=m.role,
        created_at=m.created_at,
    )
