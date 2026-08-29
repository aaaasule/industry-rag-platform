"""知识库可见性判定（02 文档：唯一入口）。"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import ROLE_ADMIN, ROLE_OWNER
from app.modules.knowledge.models import KbGrant, KnowledgeBase

PERM_READ = "read"
PERM_WRITE = "write"
PERM_MANAGE = "manage"
PERM_RANK = {PERM_READ: 1, PERM_WRITE: 2, PERM_MANAGE: 3}


def permission_covers(have: str, need: str) -> bool:
    return PERM_RANK.get(have, 0) >= PERM_RANK.get(need, 99)


async def resolve_kb_permission(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
    kb: KnowledgeBase,
    grant_map: dict[uuid.UUID, str] | None = None,
) -> str | None:
    """当前用户对单个 KB 的有效权限；与 visible_kb_ids 规则同源。"""
    if kb.tenant_id != tenant_id or kb.deleted_at is not None:
        return None
    if role in (ROLE_OWNER, ROLE_ADMIN):
        return PERM_MANAGE
    if kb.created_by == user_id:
        return PERM_MANAGE
    if grant_map is not None:
        granted = grant_map.get(kb.id)
    else:
        granted = (
            await session.execute(
                select(KbGrant.permission).where(
                    KbGrant.tenant_id == tenant_id,
                    KbGrant.user_id == user_id,
                    KbGrant.kb_id == kb.id,
                )
            )
        ).scalar_one_or_none()
    if granted:
        return granted
    if kb.visibility == "tenant":
        return PERM_READ
    return None


async def visible_kb_ids(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str,
    permission: str = PERM_READ,
) -> list[uuid.UUID]:
    """返回当前用户在本租户下具备指定权限的知识库 ID（未删除）。"""
    if permission not in PERM_RANK:
        raise ValueError(f"unknown permission: {permission}")

    kbs = list(
        (
            await session.execute(
                select(KnowledgeBase).where(
                    KnowledgeBase.tenant_id == tenant_id,
                    KnowledgeBase.deleted_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    if not kbs:
        return []

    if role in (ROLE_OWNER, ROLE_ADMIN):
        return [kb.id for kb in kbs]

    grants = list(
        (
            await session.execute(
                select(KbGrant).where(
                    KbGrant.tenant_id == tenant_id,
                    KbGrant.user_id == user_id,
                )
            )
        )
        .scalars()
        .all()
    )
    grant_map = {g.kb_id: g.permission for g in grants}

    out: list[uuid.UUID] = []
    for kb in kbs:
        have = await resolve_kb_permission(
            session,
            tenant_id=tenant_id,
            user_id=user_id,
            role=role,
            kb=kb,
            grant_map=grant_map,
        )
        if have and permission_covers(have, permission):
            out.append(kb.id)
    return out


async def kb_exists_in_tenant(
    session: AsyncSession, *, tenant_id: uuid.UUID, kb_id: uuid.UUID
) -> bool:
    row = (
        await session.execute(
            select(KnowledgeBase.id).where(
                KnowledgeBase.id == kb_id,
                KnowledgeBase.tenant_id == tenant_id,
                KnowledgeBase.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    return row is not None
