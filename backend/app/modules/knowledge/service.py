"""知识库业务逻辑。"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from app.modules.identity.permissions import (
    PERM_MANAGE,
    PERM_READ,
    PERM_WRITE,
    kb_exists_in_tenant,
    visible_kb_ids,
)
from app.modules.knowledge.models import Document, KbGrant, KnowledgeBase
from app.modules.knowledge.repository import KnowledgeRepository
from app.modules.knowledge.schemas import (
    ChunkOut,
    DocumentCreated,
    DocumentOut,
    DocumentRegisterRequest,
    GrantOut,
    GrantUpsert,
    IndustryProfileOut,
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    KnowledgeBaseUpdate,
    PreviewUrlOut,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.platform.config import Settings
from app.platform.errors import Conflict, Forbidden, NotFound, UnprocessableState
from app.platform.ids import uuid7
from app.platform.security import TokenClaims
from app.platform.storage.object_store import S3ObjectStore, document_key

# 经 API 中转上传的上限（更大文件走预签名直传）
DIRECT_UPLOAD_MAX_BYTES = 32 * 1024 * 1024


class KnowledgeService:
    def __init__(
        self,
        repo: KnowledgeRepository,
        settings: Settings,
        store: S3ObjectStore | None = None,
    ) -> None:
        self._repo = repo
        self._settings = settings
        self._store = store or S3ObjectStore(settings)

    async def list_profiles(self, tenant_id: uuid.UUID) -> list[IndustryProfileOut]:
        rows = await self._repo.list_profiles(tenant_id)
        return [IndustryProfileOut.model_validate(r) for r in rows]

    async def list_knowledge_bases(self, claims: TokenClaims) -> list[KnowledgeBaseOut]:
        ids = await visible_kb_ids(
            self._repo._session,
            tenant_id=claims.tenant_id,
            user_id=claims.user_id,
            role=claims.role,
            permission=PERM_READ,
        )
        rows = await self._repo.list_knowledge_bases(claims.tenant_id, kb_ids=ids)
        return [KnowledgeBaseOut.model_validate(r) for r in rows]

    async def create_knowledge_base(
        self, claims: TokenClaims, payload: KnowledgeBaseCreate
    ) -> KnowledgeBaseOut:
        profile = None
        if payload.profile_code:
            profile = await self._repo.get_profile_by_code(claims.tenant_id, payload.profile_code)
            # 种子未跑时允许无模板创建，避免阻塞本地冒烟
        kb = KnowledgeBase(
            tenant_id=claims.tenant_id,
            profile_id=profile.id if profile else None,
            name=payload.name,
            description=payload.description,
            embedding_model=self._settings.embedding_model,
            embedding_dim=self._settings.embedding_dim,
            visibility=payload.visibility,
            created_by=claims.user_id,
        )
        await self._repo.add_knowledge_base(kb)
        return KnowledgeBaseOut.model_validate(kb)

    async def get_knowledge_base(self, claims: TokenClaims, kb_id: uuid.UUID) -> KnowledgeBaseOut:
        kb = await self._require_kb(claims, kb_id, PERM_READ)
        return KnowledgeBaseOut.model_validate(kb)

    async def update_knowledge_base(
        self, claims: TokenClaims, kb_id: uuid.UUID, payload: KnowledgeBaseUpdate
    ) -> KnowledgeBaseOut:
        kb = await self._require_kb(claims, kb_id, PERM_WRITE)
        if payload.name is not None:
            kb.name = payload.name
        if payload.description is not None:
            kb.description = payload.description
        if payload.visibility is not None:
            kb.visibility = payload.visibility
        await self._repo._session.flush()
        return KnowledgeBaseOut.model_validate(kb)

    async def delete_knowledge_base(self, claims: TokenClaims, kb_id: uuid.UUID) -> None:
        kb = await self._require_kb(claims, kb_id, PERM_MANAGE)
        kb.deleted_at = datetime.now(UTC)

    async def list_grants(self, claims: TokenClaims, kb_id: uuid.UUID) -> list[GrantOut]:
        await self._require_kb(claims, kb_id, PERM_MANAGE)
        rows = await self._repo.list_grants(claims.tenant_id, kb_id)
        return [GrantOut.model_validate(r) for r in rows]

    async def upsert_grant(
        self,
        claims: TokenClaims,
        kb_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: GrantUpsert,
    ) -> GrantOut:
        await self._require_kb(claims, kb_id, PERM_MANAGE)
        existing = await self._repo.get_grant(claims.tenant_id, kb_id, user_id)
        if existing is None:
            row = KbGrant(
                id=uuid7(),
                tenant_id=claims.tenant_id,
                kb_id=kb_id,
                user_id=user_id,
                permission=payload.permission,
            )
            await self._repo.add_grant(row)
        else:
            existing.permission = payload.permission
            row = existing
            await self._repo._session.flush()
        return GrantOut.model_validate(row)

    async def delete_grant(
        self, claims: TokenClaims, kb_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        await self._require_kb(claims, kb_id, PERM_MANAGE)
        existing = await self._repo.get_grant(claims.tenant_id, kb_id, user_id)
        if existing is None:
            raise NotFound("授权不存在")
        await self._repo.delete_grant(existing)

    async def create_upload_url(
        self, claims: TokenClaims, kb_id: uuid.UUID, payload: UploadUrlRequest
    ) -> UploadUrlResponse:
        await self._require_kb(claims, kb_id, PERM_WRITE)
        document_id = uuid7()
        key = document_key(claims.tenant_id, document_id, payload.filename)
        signed = self._store.presign_upload(key, payload.mime_type)
        return UploadUrlResponse(
            upload_url=signed.url,
            storage_key=signed.key,
            document_id=document_id,
            expires_in=signed.expires_in,
        )

    async def register_document(
        self, claims: TokenClaims, kb_id: uuid.UUID, payload: DocumentRegisterRequest
    ) -> DocumentCreated:
        kb = await self._require_kb(claims, kb_id, PERM_WRITE)
        expected_prefix = f"tenants/{claims.tenant_id}/documents/{payload.document_id}/"
        if not payload.storage_key.startswith(expected_prefix):
            raise Conflict("storage_key 与租户/文档不匹配", code="invalid_storage_key")

        dup = await self._repo.find_by_checksum(kb_id, payload.checksum)
        if dup is not None:
            raise Conflict("同知识库已存在相同文件", code="duplicate_document")

        doc = Document(
            id=payload.document_id,
            tenant_id=claims.tenant_id,
            kb_id=kb.id,
            title=payload.title,
            source_type="upload",
            mime_type=payload.mime_type,
            file_size=payload.file_size,
            checksum=payload.checksum,
            storage_key=payload.storage_key,
            meta=payload.metadata,
            uploaded_by=claims.user_id,
        )
        await self._repo.add_document(doc)
        kb.doc_count += 1

        from app.modules.ingestion.service import enqueue_ingest

        job_id = await enqueue_ingest(doc.id, claims.tenant_id, self._repo._session)
        return DocumentCreated(document_id=doc.id, status=doc.status, job_id=job_id)

    async def upload_document(
        self,
        claims: TokenClaims,
        kb_id: uuid.UUID,
        *,
        filename: str,
        content_type: str,
        data: bytes,
        title: str | None = None,
    ) -> DocumentCreated:
        if len(data) == 0:
            raise UnprocessableState("空文件")
        if len(data) > DIRECT_UPLOAD_MAX_BYTES:
            raise UnprocessableState(
                f"文件超过 {DIRECT_UPLOAD_MAX_BYTES // (1024 * 1024)}MB，请使用预签名直传"
            )

        await self._require_kb(claims, kb_id, PERM_WRITE)
        document_id = uuid7()
        key = document_key(claims.tenant_id, document_id, filename)
        mime = content_type or "application/octet-stream"
        self._store.put(key, data, mime)
        checksum = "sha256:" + hashlib.sha256(data).hexdigest()
        return await self.register_document(
            claims,
            kb_id,
            DocumentRegisterRequest(
                storage_key=key,
                document_id=document_id,
                title=title or filename,
                checksum=checksum,
                file_size=len(data),
                mime_type=mime,
            ),
        )

    async def list_documents(self, claims: TokenClaims, kb_id: uuid.UUID) -> list[DocumentOut]:
        await self._require_kb(claims, kb_id, PERM_READ)
        rows = await self._repo.list_documents(claims.tenant_id, kb_id)
        return [DocumentOut.model_validate(r) for r in rows]

    async def get_document(self, claims: TokenClaims, doc_id: uuid.UUID) -> DocumentOut:
        doc = await self._require_doc(claims, doc_id, PERM_READ)
        return DocumentOut.model_validate(doc)

    async def delete_document(self, claims: TokenClaims, doc_id: uuid.UUID) -> None:
        doc = await self._require_doc(claims, doc_id, PERM_WRITE)
        doc.deleted_at = datetime.now(UTC)
        kb = await self._require_kb(claims, doc.kb_id, PERM_WRITE)
        kb.doc_count = max(0, kb.doc_count - 1)

    async def reingest(self, claims: TokenClaims, doc_id: uuid.UUID) -> DocumentCreated:
        doc = await self._require_doc(claims, doc_id, PERM_WRITE)
        from app.modules.ingestion.service import enqueue_ingest

        job_id = await enqueue_ingest(doc.id, claims.tenant_id, self._repo._session, force=True)
        return DocumentCreated(document_id=doc.id, status=doc.status, job_id=job_id)

    async def preview_url(self, claims: TokenClaims, doc_id: uuid.UUID) -> PreviewUrlOut:
        doc = await self._require_doc(claims, doc_id, PERM_READ)
        url = self._store.presign_download(doc.storage_key)
        return PreviewUrlOut(url=url, expires_in=self._settings.s3_presign_ttl_seconds)

    async def list_chunks(self, claims: TokenClaims, doc_id: uuid.UUID) -> list[ChunkOut]:
        await self._require_doc(claims, doc_id, PERM_READ)
        rows = await self._repo.list_chunks(claims.tenant_id, doc_id)
        return [
            ChunkOut(
                id=c.id,
                seq=c.seq,
                content=c.raw_content,
                heading_path=list(c.heading_path or []),
                page_start=c.page_start,
                page_end=c.page_end,
                bboxes=list(c.bboxes or []),
                chunk_type=c.chunk_type,
            )
            for c in rows
        ]

    async def _require_kb(
        self, claims: TokenClaims, kb_id: uuid.UUID, permission: str
    ) -> KnowledgeBase:
        kb = await self._repo.get_knowledge_base(claims.tenant_id, kb_id)
        if kb is None:
            raise NotFound("知识库不存在")
        ids = await visible_kb_ids(
            self._repo._session,
            tenant_id=claims.tenant_id,
            user_id=claims.user_id,
            role=claims.role,
            permission=permission,
        )
        if kb.id not in ids:
            # 同租户存在但无权 → 403；避免与跨租户 404 混淆
            if await kb_exists_in_tenant(
                self._repo._session, tenant_id=claims.tenant_id, kb_id=kb_id
            ):
                raise Forbidden("没有权限访问该知识库")
            raise NotFound("知识库不存在")
        return kb

    async def _require_doc(
        self, claims: TokenClaims, doc_id: uuid.UUID, permission: str
    ) -> Document:
        doc = await self._repo.get_document(claims.tenant_id, doc_id)
        if doc is None:
            raise NotFound("文档不存在")
        await self._require_kb(claims, doc.kb_id, permission)
        return doc
