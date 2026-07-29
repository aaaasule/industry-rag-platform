"""知识库数据访问。"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import Document, IndustryProfile, KnowledgeBase


class KnowledgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_profiles(self, tenant_id: uuid.UUID) -> list[IndustryProfile]:
        stmt = (
            select(IndustryProfile)
            .where((IndustryProfile.tenant_id.is_(None)) | (IndustryProfile.tenant_id == tenant_id))
            .order_by(IndustryProfile.is_builtin.desc(), IndustryProfile.code)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_profile_by_code(self, tenant_id: uuid.UUID, code: str) -> IndustryProfile | None:
        # 租户自定义优先于内置
        tenant_row = (
            await self._session.execute(
                select(IndustryProfile).where(
                    IndustryProfile.code == code, IndustryProfile.tenant_id == tenant_id
                )
            )
        ).scalar_one_or_none()
        if tenant_row:
            return tenant_row
        return (
            await self._session.execute(
                select(IndustryProfile).where(
                    IndustryProfile.code == code, IndustryProfile.tenant_id.is_(None)
                )
            )
        ).scalar_one_or_none()

    async def list_knowledge_bases(self, tenant_id: uuid.UUID) -> list[KnowledgeBase]:
        stmt = (
            select(KnowledgeBase)
            .where(KnowledgeBase.tenant_id == tenant_id, KnowledgeBase.deleted_at.is_(None))
            .order_by(KnowledgeBase.created_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_knowledge_base(
        self, tenant_id: uuid.UUID, kb_id: uuid.UUID
    ) -> KnowledgeBase | None:
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.tenant_id == tenant_id,
            KnowledgeBase.deleted_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add_knowledge_base(self, kb: KnowledgeBase) -> KnowledgeBase:
        self._session.add(kb)
        await self._session.flush()
        return kb

    async def list_documents(self, tenant_id: uuid.UUID, kb_id: uuid.UUID) -> list[Document]:
        stmt = (
            select(Document)
            .where(
                Document.tenant_id == tenant_id,
                Document.kb_id == kb_id,
                Document.deleted_at.is_(None),
            )
            .order_by(Document.created_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_document(self, tenant_id: uuid.UUID, doc_id: uuid.UUID) -> Document | None:
        stmt = select(Document).where(
            Document.id == doc_id,
            Document.tenant_id == tenant_id,
            Document.deleted_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def find_by_checksum(self, kb_id: uuid.UUID, checksum: str) -> Document | None:
        stmt = select(Document).where(
            Document.kb_id == kb_id,
            Document.checksum == checksum,
            Document.deleted_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add_document(self, doc: Document) -> Document:
        self._session.add(doc)
        await self._session.flush()
        return doc
