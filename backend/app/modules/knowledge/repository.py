"""知识库数据访问。"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import (
    Chunk,
    Document,
    DocumentPage,
    IndustryProfile,
    KbGrant,
    KnowledgeBase,
)


class KnowledgeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_profiles(self, tenant_id: uuid.UUID) -> list[IndustryProfile]:
        stmt = (
            select(IndustryProfile)
            .where(
                (IndustryProfile.tenant_id.is_(None)) | (IndustryProfile.tenant_id == tenant_id),
                IndustryProfile.deleted_at.is_(None),
            )
            .order_by(IndustryProfile.is_builtin.desc(), IndustryProfile.code)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_profile_by_code(self, tenant_id: uuid.UUID, code: str) -> IndustryProfile | None:
        # 租户自定义优先于内置
        tenant_row = (
            await self._session.execute(
                select(IndustryProfile).where(
                    IndustryProfile.code == code,
                    IndustryProfile.tenant_id == tenant_id,
                    IndustryProfile.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        if tenant_row:
            return tenant_row
        return (
            await self._session.execute(
                select(IndustryProfile).where(
                    IndustryProfile.code == code,
                    IndustryProfile.tenant_id.is_(None),
                    IndustryProfile.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()

    async def get_profile(
        self, tenant_id: uuid.UUID, profile_id: uuid.UUID
    ) -> IndustryProfile | None:
        """本租户自定义或全局内置。"""
        return (
            await self._session.execute(
                select(IndustryProfile).where(
                    IndustryProfile.id == profile_id,
                    (IndustryProfile.tenant_id.is_(None))
                    | (IndustryProfile.tenant_id == tenant_id),
                    IndustryProfile.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()

    async def tenant_profile_code_exists(self, tenant_id: uuid.UUID, code: str) -> bool:
        row = (
            await self._session.execute(
                select(IndustryProfile.id).where(
                    IndustryProfile.code == code,
                    IndustryProfile.tenant_id == tenant_id,
                    IndustryProfile.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()
        return row is not None

    async def count_kbs_with_profile(self, profile_id: uuid.UUID) -> int:
        """统计仍绑定该模板且未软删的知识库数量。"""
        result = await self._session.execute(
            select(func.count())
            .select_from(KnowledgeBase)
            .where(
                KnowledgeBase.profile_id == profile_id,
                KnowledgeBase.deleted_at.is_(None),
            )
        )
        return int(result.scalar_one())

    async def add_profile(self, profile: IndustryProfile) -> IndustryProfile:
        self._session.add(profile)
        await self._session.flush()
        return profile

    async def list_knowledge_bases(
        self, tenant_id: uuid.UUID, *, kb_ids: list[uuid.UUID] | None = None
    ) -> list[KnowledgeBase]:
        stmt = select(KnowledgeBase).where(
            KnowledgeBase.tenant_id == tenant_id, KnowledgeBase.deleted_at.is_(None)
        )
        if kb_ids is not None:
            if not kb_ids:
                return []
            stmt = stmt.where(KnowledgeBase.id.in_(kb_ids))
        stmt = stmt.order_by(KnowledgeBase.created_at.desc())
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

    async def list_grants(self, tenant_id: uuid.UUID, kb_id: uuid.UUID) -> list[KbGrant]:
        stmt = (
            select(KbGrant)
            .where(KbGrant.tenant_id == tenant_id, KbGrant.kb_id == kb_id)
            .order_by(KbGrant.created_at.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_grant(
        self, tenant_id: uuid.UUID, kb_id: uuid.UUID, user_id: uuid.UUID
    ) -> KbGrant | None:
        stmt = select(KbGrant).where(
            KbGrant.tenant_id == tenant_id,
            KbGrant.kb_id == kb_id,
            KbGrant.user_id == user_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add_grant(self, grant: KbGrant) -> KbGrant:
        self._session.add(grant)
        await self._session.flush()
        return grant

    async def delete_grant(self, grant: KbGrant) -> None:
        await self._session.delete(grant)
        await self._session.flush()

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

    async def list_pages(self, tenant_id: uuid.UUID, doc_id: uuid.UUID) -> list[DocumentPage]:
        stmt = (
            select(DocumentPage)
            .where(DocumentPage.tenant_id == tenant_id, DocumentPage.document_id == doc_id)
            .order_by(DocumentPage.page_no.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def list_chunks(self, tenant_id: uuid.UUID, doc_id: uuid.UUID) -> list[Chunk]:
        stmt = (
            select(Chunk)
            .where(Chunk.tenant_id == tenant_id, Chunk.document_id == doc_id)
            .order_by(Chunk.seq.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())
