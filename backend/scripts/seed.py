"""开发种子数据。

幂等：重复执行不会产生重复数据，也不会覆盖已修改的口令。
仅允许在 local 环境运行——种子口令是公开的。
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.modules.identity.models import (
    ROLE_ADMIN,
    ROLE_MEMBER,
    ROLE_OWNER,
    Membership,
    Tenant,
    User,
)
from app.platform.config import get_settings
from app.platform.db import session_scope
from app.platform.logging import configure_logging, get_logger
from app.platform.security import hash_password

logger = get_logger(__name__)

SEED_PASSWORD = "Passw0rd!2026"

TENANTS = [
    ("acme-machinery", "艾克姆装备制造"),
    ("north-chem", "北方化工"),
]

USERS = [
    ("owner@acme.example", "王建国"),
    ("admin@acme.example", "李敏"),
    ("member@acme.example", "张伟"),
    ("owner@northchem.example", "赵芳"),
]

# (tenant_slug, email, role)。owner@acme.example 刻意同属两个租户，用于验证租户切换
MEMBERSHIPS = [
    ("acme-machinery", "owner@acme.example", ROLE_OWNER),
    ("acme-machinery", "admin@acme.example", ROLE_ADMIN),
    ("acme-machinery", "member@acme.example", ROLE_MEMBER),
    ("north-chem", "owner@northchem.example", ROLE_OWNER),
    ("north-chem", "owner@acme.example", ROLE_MEMBER),
]


async def seed() -> None:
    settings = get_settings()
    if not settings.is_local:
        logger.error("seed_rejected", environment=settings.environment)
        sys.exit(1)

    tenant_ids, user_ids = await _seed_principals()
    # memberships 有 RLS，写入必须带租户上下文，因此按租户分事务
    for slug, tenant_id in tenant_ids.items():
        rows = [(email, role) for s, email, role in MEMBERSHIPS if s == slug]
        await _seed_memberships(slug, tenant_id, user_ids, rows)

    logger.info("seed_completed", password=SEED_PASSWORD)


async def _seed_principals() -> tuple[dict[str, object], dict[str, object]]:
    tenant_ids: dict[str, object] = {}
    user_ids: dict[str, object] = {}
    password_hash = hash_password(SEED_PASSWORD)

    async with session_scope() as session:
        for slug, name in TENANTS:
            tenant = (
                await session.execute(select(Tenant).where(Tenant.slug == slug))
            ).scalar_one_or_none()
            if tenant is None:
                tenant = Tenant(
                    slug=slug,
                    name=name,
                    quota={"max_documents": 10_000, "monthly_tokens": 50_000_000},
                )
                session.add(tenant)
                await session.flush()
                logger.info("tenant_created", slug=slug)
            tenant_ids[slug] = tenant.id

        for email, display_name in USERS:
            user = (
                await session.execute(select(User).where(User.email == email))
            ).scalar_one_or_none()
            if user is None:
                user = User(email=email, display_name=display_name, password_hash=password_hash)
                session.add(user)
                await session.flush()
                logger.info("user_created", email=email)
            user_ids[email] = user.id

    return tenant_ids, user_ids


async def _seed_memberships(
    slug: str,
    tenant_id: object,
    user_ids: dict[str, object],
    rows: list[tuple[str, str]],
) -> None:
    async with session_scope(tenant_id=tenant_id) as session:  # type: ignore[arg-type]
        for email, role in rows:
            user_id = user_ids[email]
            exists = (
                await session.execute(
                    select(Membership.id).where(
                        Membership.user_id == user_id,
                        Membership.tenant_id == tenant_id,
                    )
                )
            ).scalar_one_or_none()
            if exists is None:
                session.add(
                    Membership(tenant_id=tenant_id, user_id=user_id, role=role)  # type: ignore[arg-type]
                )
                logger.info("membership_created", email=email, tenant=slug, role=role)


if __name__ == "__main__":
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)
    asyncio.run(seed())
