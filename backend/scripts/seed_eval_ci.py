"""CI 评测专用种子数据（幂等，固定 KB/Document UUID）。

仅允许在 local 环境运行——口令写在仓库里供 CI 使用。
重复执行不会覆盖已有用户口令，也不会重复插入 chunk。
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.identity.models import ROLE_OWNER, Membership, Tenant, User
from app.modules.ingestion.chunkers.tsv import build_tsv
from app.modules.knowledge.models import Chunk, Document, IndustryProfile, KnowledgeBase
from app.platform.config import get_settings
from app.platform.db import session_scope
from app.platform.ids import uuid7
from app.platform.llm.fake import FakeEmbeddingProvider
from app.platform.logging import configure_logging, get_logger
from app.platform.security import hash_password

logger = get_logger(__name__)

TENANT_SLUG = "eval-ci"
TENANT_NAME = "Eval CI"
EMAIL = "eval-ci@example.com"
DISPLAY_NAME = "Eval CI"
PASSWORD = "EvalCI-Passw0rd!"
KB_ID = uuid.UUID("01900000-0000-7000-8000-000000000001")
DOC_ID = uuid.UUID("01900000-0000-7000-8000-000000000002")
CHUNK_MARKER = "EVAL_CI_MARKER_HYD2201_保养周期为三个月"
CHUNK_CONTENT = f"液压泵 HYD-2201 保养说明。{CHUNK_MARKER}。"

GENERAL_PROFILE: dict[str, Any] = {
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
}


async def seed() -> None:
    settings = get_settings()
    if not settings.is_local:
        logger.error("seed_eval_ci_rejected", environment=settings.environment)
        sys.exit(1)

    profile_id = await _ensure_general_profile()
    tenant_id, user_id = await _ensure_principal()
    await _ensure_membership(tenant_id, user_id)
    await _ensure_kb_doc_chunk(tenant_id, user_id, profile_id, settings.embedding_dim)

    logger.info(
        "seed_eval_ci_completed",
        tenant=TENANT_SLUG,
        email=EMAIL,
        kb_id=str(KB_ID),
        doc_id=str(DOC_ID),
    )


async def _ensure_general_profile() -> uuid.UUID:
    """内置 general 的 tenant_id 为 NULL，需迁移角色绕过 RLS。"""
    settings = get_settings()
    url = settings.database_migration_url or settings.database_url
    engine = create_async_engine(url, pool_pre_ping=True)
    maker = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    try:
        async with maker() as session:
            existing = (
                await session.execute(
                    select(IndustryProfile).where(
                        IndustryProfile.code == "general",
                        IndustryProfile.tenant_id.is_(None),
                    )
                )
            ).scalar_one_or_none()
            if existing is not None:
                await session.commit()
                return existing.id
            profile = IndustryProfile(
                id=uuid7(),
                tenant_id=None,
                code=GENERAL_PROFILE["code"],
                name=GENERAL_PROFILE["name"],
                parse_rules=GENERAL_PROFILE["parse_rules"],
                chunk_rules=GENERAL_PROFILE["chunk_rules"],
                metadata_schema=GENERAL_PROFILE["metadata_schema"],
                prompt_overrides=GENERAL_PROFILE["prompt_overrides"],
                retrieval_rules=GENERAL_PROFILE["retrieval_rules"],
                is_builtin=True,
            )
            session.add(profile)
            await session.commit()
            logger.info("profile_created", code="general")
            return profile.id
    finally:
        await engine.dispose()


async def _ensure_principal() -> tuple[uuid.UUID, uuid.UUID]:
    password_hash = hash_password(PASSWORD)
    async with session_scope() as session:
        tenant = (
            await session.execute(select(Tenant).where(Tenant.slug == TENANT_SLUG))
        ).scalar_one_or_none()
        if tenant is None:
            tenant = Tenant(
                slug=TENANT_SLUG,
                name=TENANT_NAME,
                quota={"max_documents": 100, "monthly_tokens": 1_000_000},
            )
            session.add(tenant)
            await session.flush()
            logger.info("tenant_created", slug=TENANT_SLUG)
        else:
            logger.info("tenant_exists", slug=TENANT_SLUG)

        user = (await session.execute(select(User).where(User.email == EMAIL))).scalar_one_or_none()
        if user is None:
            user = User(
                email=EMAIL,
                display_name=DISPLAY_NAME,
                password_hash=password_hash,
            )
            session.add(user)
            await session.flush()
            logger.info("user_created", email=EMAIL)
        else:
            logger.info("user_exists", email=EMAIL)

        return tenant.id, user.id


async def _ensure_membership(tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
    async with session_scope(tenant_id=tenant_id) as session:
        exists = (
            await session.execute(
                select(Membership.id).where(
                    Membership.user_id == user_id,
                    Membership.tenant_id == tenant_id,
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            session.add(Membership(tenant_id=tenant_id, user_id=user_id, role=ROLE_OWNER))
            logger.info("membership_created", email=EMAIL, role=ROLE_OWNER)
        else:
            logger.info("membership_exists", email=EMAIL)


async def _ensure_kb_doc_chunk(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    profile_id: uuid.UUID,
    embedding_dim: int,
) -> None:
    emb = FakeEmbeddingProvider(dimension=embedding_dim)
    vectors = await emb.embed([CHUNK_CONTENT], input_type="document")
    vector = vectors[0]

    async with session_scope(tenant_id=tenant_id, user_id=user_id) as session:
        kb = (
            await session.execute(select(KnowledgeBase).where(KnowledgeBase.id == KB_ID))
        ).scalar_one_or_none()
        if kb is None:
            kb = KnowledgeBase(
                id=KB_ID,
                tenant_id=tenant_id,
                profile_id=profile_id,
                name="Eval CI KB",
                description="CI retrieval golden fixture",
                embedding_model="fake",
                embedding_dim=embedding_dim,
                created_by=user_id,
                doc_count=0,
                chunk_count=0,
            )
            session.add(kb)
            await session.flush()
            logger.info("kb_created", kb_id=str(KB_ID))
        else:
            logger.info("kb_exists", kb_id=str(KB_ID))

        doc = (
            await session.execute(select(Document).where(Document.id == DOC_ID))
        ).scalar_one_or_none()
        if doc is None:
            doc = Document(
                id=DOC_ID,
                tenant_id=tenant_id,
                kb_id=KB_ID,
                title="Eval CI 保养手册",
                source_type="upload",
                mime_type="text/plain",
                file_size=len(CHUNK_CONTENT.encode("utf-8")),
                checksum="sha256:eval-ci-marker-hyd2201",
                storage_key=f"tenants/{tenant_id}/documents/{DOC_ID}/original.txt",
                status="ready",
                page_count=1,
                uploaded_by=user_id,
            )
            session.add(doc)
            await session.flush()
            kb.doc_count = (kb.doc_count or 0) + 1
            logger.info("document_created", doc_id=str(DOC_ID))
        else:
            logger.info("document_exists", doc_id=str(DOC_ID))

        chunk_exists = (
            await session.execute(
                select(Chunk.id).where(Chunk.document_id == DOC_ID, Chunk.seq == 0)
            )
        ).scalar_one_or_none()
        if chunk_exists is None:
            tsv_text = build_tsv(CHUNK_CONTENT)
            tsv_value = (
                await session.execute(select(func.to_tsvector("simple", tsv_text)))
            ).scalar_one()
            session.add(
                Chunk(
                    tenant_id=tenant_id,
                    kb_id=KB_ID,
                    document_id=DOC_ID,
                    seq=0,
                    content=CHUNK_CONTENT,
                    raw_content=CHUNK_CONTENT,
                    heading_path=["保养"],
                    chunk_type="text",
                    page_start=1,
                    page_end=1,
                    bboxes=[],
                    token_count=max(1, len(CHUNK_CONTENT) // 2),
                    embedding=vector,
                    tsv=tsv_value,
                )
            )
            kb.chunk_count = (kb.chunk_count or 0) + 1
            logger.info("chunk_created", document_id=str(DOC_ID), seq=0)
        else:
            logger.info("chunk_exists", document_id=str(DOC_ID), seq=0)


if __name__ == "__main__":
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)
    asyncio.run(seed())
