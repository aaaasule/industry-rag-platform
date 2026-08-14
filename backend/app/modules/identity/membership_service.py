"""租户成员管理业务逻辑。"""

from __future__ import annotations

import secrets
import string
import uuid

from app.modules.audit.service import AuditService
from app.modules.identity.models import ROLE_OWNER, ROLES, Membership, User, role_at_least
from app.modules.identity.repository import IdentityRepository
from app.modules.identity.schemas import MemberCreate, MemberOut, MemberRoleUpdate, MembershipList
from app.platform.errors import AppError, Conflict, Forbidden, NotFound
from app.platform.ids import uuid7
from app.platform.security import TokenClaims, hash_password


def _generate_temporary_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    # 保证至少含大小写与数字，满足登录 min_length=8
    parts = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
    ]
    parts.extend(secrets.choice(alphabet) for _ in range(max(0, length - len(parts))))
    secrets.SystemRandom().shuffle(parts)
    return "".join(parts)


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

        email = str(payload.email).lower()
        user = await self._repo.get_user_by_email(email)
        created_user = False
        temporary_password: str | None = None

        if user is None:
            if not payload.create_if_missing:
                raise NotFound("user not found")
            temporary_password = _generate_temporary_password()
            display = (payload.display_name or email.split("@", 1)[0]).strip() or email
            user = User(
                id=uuid7(),
                email=email,
                display_name=display[:128],
                password_hash=hash_password(temporary_password),
                status="active",
            )
            await self._repo.add_user(user)
            created_user = True

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
        membership.user = user

        await self._audit.record(
            tenant_id=claims.tenant_id,
            actor_id=claims.user_id,
            action="membership.add",
            target_type="membership",
            target_id=membership.id,
            payload={
                "email": user.email,
                "role": role,
                "user_id": str(user.id),
                "created_user": created_user,
            },
        )
        return _member_out(
            membership,
            created_user=created_user,
            temporary_password=temporary_password,
        )

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

        if membership.role == ROLE_OWNER and await self._repo.count_owners(claims.tenant_id) <= 1:
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


def _member_out(
    m: Membership,
    *,
    created_user: bool = False,
    temporary_password: str | None = None,
) -> MemberOut:
    user = m.user
    return MemberOut(
        user_id=m.user_id,
        email=user.email,
        display_name=user.display_name,
        role=m.role,
        created_at=m.created_at,
        created_user=created_user,
        temporary_password=temporary_password,
    )
