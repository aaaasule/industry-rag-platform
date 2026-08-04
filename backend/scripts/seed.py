"""开发种子数据。

幂等：重复执行不会产生重复数据，也不会覆盖已修改的口令。
仅允许在 local 环境运行——种子口令是公开的。
"""

from __future__ import annotations

import asyncio
import sys
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.identity.models import (
    ROLE_ADMIN,
    ROLE_MEMBER,
    ROLE_OWNER,
    Membership,
    Tenant,
    User,
)
from app.modules.knowledge.models import IndustryProfile
from app.platform.config import get_settings
from app.platform.db import session_scope
from app.platform.ids import uuid7
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

BUILTIN_PROFILES: list[dict[str, Any]] = [
    {
        "code": "general",
        "name": "通用",
        "chunk_rules": {
            "max_tokens": 512,
            "min_tokens": 80,
            "overlap_tokens": 64,
            "clause_mode": False,
            "keep_heading_prefix": True,
        },
        "parse_rules": {},
        "metadata_schema": {},
        "prompt_overrides": {},
        "retrieval_rules": {"top_k": 8},
    },
    {
        "code": "discrete_manufacturing",
        "name": "离散制造",
        "chunk_rules": {
            "max_tokens": 512,
            "min_tokens": 80,
            "overlap_tokens": 64,
            "clause_mode": False,
            "keep_heading_prefix": True,
        },
        "parse_rules": {},
        "metadata_schema": {"equipment_model": {"type": "string"}},
        "prompt_overrides": {},
        "retrieval_rules": {"top_k": 8},
    },
    {
        "code": "process_industry",
        "name": "流程工业",
        "chunk_rules": {
            "max_tokens": 480,
            "min_tokens": 60,
            "overlap_tokens": 48,
            "clause_mode": True,
            "keep_heading_prefix": True,
        },
        "parse_rules": {},
        "metadata_schema": {"standard_no": {"type": "string"}},
        "prompt_overrides": {},
        "retrieval_rules": {"top_k": 10},
    },
]


async def seed() -> None:
    settings = get_settings()
    if not settings.is_local:
        logger.error("seed_rejected", environment=settings.environment)
        sys.exit(1)

    await _seed_builtin_profiles()
    await _seed_platform_model_connections()
    await _seed_model_pricing()
    tenant_ids, user_ids = await _seed_principals()
    for slug, tenant_id in tenant_ids.items():
        rows = [(email, role) for s, email, role in MEMBERSHIPS if s == slug]
        await _seed_memberships(slug, tenant_id, user_ids, rows)

    logger.info("seed_completed", password=SEED_PASSWORD)


async def _seed_platform_model_connections() -> None:
    """从 IRP_* 环境变量幂等写入平台级接入点（迁移角色绕过 RLS）。"""
    from app.modules.modelops.credentials import credential_hint, encrypt_credential
    from app.modules.modelops.models import (
        PURPOSE_CHAT,
        PURPOSE_EMBEDDING,
        PURPOSE_RERANK,
        ModelConnection,
    )

    settings = get_settings()
    url = settings.database_migration_url or settings.database_url
    engine = create_async_engine(url, pool_pre_ping=True)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)

    specs = [
        (
            "platform-chat",
            settings.llm_provider,
            settings.llm_base_url,
            settings.llm_api_key.get_secret_value(),
            settings.llm_model,
            [PURPOSE_CHAT, "title"],
            100,
        ),
        (
            "platform-embedding",
            settings.embedding_provider,
            settings.resolved_embedding_base_url,
            settings.resolved_embedding_api_key,
            settings.embedding_model,
            [PURPOSE_EMBEDDING],
            100,
        ),
        (
            "platform-rerank",
            settings.resolved_rerank_provider,
            settings.resolved_rerank_base_url,
            settings.resolved_rerank_api_key,
            settings.rerank_model,
            [PURPOSE_RERANK],
            100,
        ),
    ]

    try:
        async with maker() as session:
            for name, provider_type, base_url, api_key, model, purposes, priority in specs:
                exists = (
                    await session.execute(
                        select(ModelConnection.id).where(
                            ModelConnection.tenant_id.is_(None),
                            ModelConnection.name == name,
                        )
                    )
                ).scalar_one_or_none()
                if exists is not None:
                    continue
                extra: dict[str, Any] = {}
                if PURPOSE_EMBEDDING in purposes:
                    extra["embedding_dim"] = settings.embedding_dim
                    extra["batch_size"] = settings.embedding_batch_size
                if PURPOSE_RERANK in purposes:
                    extra["rerank_path"] = settings.rerank_path
                session.add(
                    ModelConnection(
                        id=uuid7(),
                        tenant_id=None,
                        name=name,
                        provider_type=provider_type,
                        base_url=base_url or "http://localhost",
                        credential_cipher=encrypt_credential(api_key or "", settings),
                        credential_hint=credential_hint(api_key or ""),
                        model=model,
                        purposes=purposes,
                        priority=priority,
                        enabled=True,
                        extra=extra,
                        version=1,
                    )
                )
                logger.info("platform_connection_created", name=name, purposes=purposes)
            await session.commit()
    finally:
        await engine.dispose()


async def _seed_model_pricing() -> None:
    """占位定价（开发用），幂等按 provider+model+effective_from。"""
    from datetime import UTC, datetime
    from decimal import Decimal

    from app.modules.modelops.usage_models import ModelPricing

    settings = get_settings()
    url = settings.database_migration_url or settings.database_url
    engine = create_async_engine(url, pool_pre_ping=True)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    effective_from = datetime(2026, 1, 1, tzinfo=UTC)
    rows = [
        ("fake", settings.llm_model, Decimal("0.001000"), Decimal("0.002000")),
        ("fake", settings.embedding_model, Decimal("0.000100"), Decimal("0")),
        ("fake", settings.rerank_model, Decimal("0.000200"), Decimal("0")),
        (
            "openai_compatible",
            settings.llm_model,
            Decimal("0.150000"),
            Decimal("0.600000"),
        ),
        (
            "openai_compatible",
            settings.embedding_model,
            Decimal("0.020000"),
            Decimal("0"),
        ),
        (
            "openai_compatible",
            settings.rerank_model,
            Decimal("0.010000"),
            Decimal("0"),
        ),
    ]
    try:
        async with maker() as session:
            for provider_type, model, prompt_p, completion_p in rows:
                exists = (
                    await session.execute(
                        select(ModelPricing.id).where(
                            ModelPricing.provider_type == provider_type,
                            ModelPricing.model == model,
                            ModelPricing.effective_from == effective_from,
                        )
                    )
                ).scalar_one_or_none()
                if exists is not None:
                    continue
                session.add(
                    ModelPricing(
                        id=uuid7(),
                        provider_type=provider_type,
                        model=model,
                        prompt_price_per_1k=prompt_p,
                        completion_price_per_1k=completion_p,
                        currency="USD",
                        effective_from=effective_from,
                        effective_to=None,
                    )
                )
                logger.info("model_pricing_seeded", provider=provider_type, model=model)
            await session.commit()
    finally:
        await engine.dispose()


async def _seed_builtin_profiles() -> None:
    """内置 profile 的 tenant_id 为 NULL，需用迁移角色写入（超级用户绕过 RLS）。"""
    settings = get_settings()
    url = settings.database_migration_url or settings.database_url
    engine = create_async_engine(url, pool_pre_ping=True)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with maker() as session:
            for spec in BUILTIN_PROFILES:
                exists = (
                    await session.execute(
                        select(IndustryProfile.id).where(
                            IndustryProfile.code == spec["code"],
                            IndustryProfile.tenant_id.is_(None),
                        )
                    )
                ).scalar_one_or_none()
                if exists is not None:
                    continue
                session.add(
                    IndustryProfile(
                        id=uuid7(),
                        tenant_id=None,
                        code=spec["code"],
                        name=spec["name"],
                        parse_rules=spec["parse_rules"],
                        chunk_rules=spec["chunk_rules"],
                        metadata_schema=spec["metadata_schema"],
                        prompt_overrides=spec["prompt_overrides"],
                        retrieval_rules=spec["retrieval_rules"],
                        is_builtin=True,
                    )
                )
                logger.info("profile_created", code=spec["code"])
            await session.commit()
    finally:
        await engine.dispose()


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
