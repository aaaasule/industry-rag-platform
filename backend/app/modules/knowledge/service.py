"""知识库业务逻辑。"""

from __future__ import annotations

import copy
import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from app.modules.audit.service import AuditService
from app.modules.identity.permissions import (
    PERM_MANAGE,
    PERM_READ,
    PERM_WRITE,
    kb_exists_in_tenant,
    visible_kb_ids,
)
from app.modules.knowledge.models import Document, IndustryProfile, KbGrant, KnowledgeBase
from app.modules.knowledge.repository import KnowledgeRepository
from app.modules.knowledge.schemas import (
    ChunkOut,
    DocumentCreated,
    DocumentOut,
    DocumentPageOut,
    DocumentRegisterRequest,
    GrantOut,
    GrantUpsert,
    IndustryProfileCreate,
    IndustryProfileOut,
    IndustryProfileUpdate,
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    KnowledgeBaseUpdate,
    PreviewUrlOut,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.modules.profile.schemas import (
    ChunkRulesConfig,
    ParseRulesConfig,
    PromptOverridesConfig,
    RetrievalRulesConfig,
)
from app.platform.config import Settings
from app.platform.errors import AppError, Conflict, Forbidden, NotFound, UnprocessableState
from app.platform.ids import uuid7
from app.platform.security import TokenClaims
from app.platform.storage.object_store import S3ObjectStore, document_key


def _validate_profile_rules(
    *,
    chunk_rules: dict[str, Any] | None = None,
    prompt_overrides: dict[str, Any] | None = None,
    retrieval_rules: dict[str, Any] | None = None,
    parse_rules: dict[str, Any] | None = None,
) -> None:
    try:
        if chunk_rules is not None:
            ChunkRulesConfig.model_validate(chunk_rules)
        if prompt_overrides is not None:
            PromptOverridesConfig.model_validate(prompt_overrides)
        if retrieval_rules is not None:
            RetrievalRulesConfig.model_validate(retrieval_rules)
        if parse_rules is not None:
            ParseRulesConfig.model_validate(parse_rules)
    except ValidationError as exc:
        raise AppError(
            "行业配置字段校验失败",
            code="validation_error",
            details={"errors": exc.errors()},
        ) from exc


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

    async def list_profiles(
        self, tenant_id: uuid.UUID, *, include_deleted: bool = False
    ) -> list[IndustryProfileOut]:
        rows = await self._repo.list_profiles(tenant_id)
        if include_deleted:
            rows = [*rows, *await self._repo.list_deleted_tenant_profiles(tenant_id)]
        return [IndustryProfileOut.model_validate(r) for r in rows]

    async def create_profile(
        self, claims: TokenClaims, payload: IndustryProfileCreate
    ) -> IndustryProfileOut:
        base = await self._repo.get_profile_by_code(claims.tenant_id, payload.base_code)
        if base is None:
            raise NotFound("基础行业模板不存在", code="profile_not_found")
        if await self._repo.tenant_profile_code_exists(claims.tenant_id, payload.code):
            raise Conflict("本租户已存在相同 code", code="duplicate_profile_code")

        chunk_rules = (
            copy.deepcopy(payload.chunk_rules)
            if payload.chunk_rules is not None
            else copy.deepcopy(base.chunk_rules)
        )
        prompt_overrides = (
            copy.deepcopy(payload.prompt_overrides)
            if payload.prompt_overrides is not None
            else copy.deepcopy(base.prompt_overrides)
        )
        retrieval_rules = (
            copy.deepcopy(payload.retrieval_rules)
            if payload.retrieval_rules is not None
            else copy.deepcopy(base.retrieval_rules)
        )
        parse_rules = (
            copy.deepcopy(payload.parse_rules)
            if payload.parse_rules is not None
            else copy.deepcopy(base.parse_rules)
        )
        metadata_schema = (
            copy.deepcopy(payload.metadata_schema)
            if payload.metadata_schema is not None
            else copy.deepcopy(base.metadata_schema)
        )
        _validate_profile_rules(
            chunk_rules=chunk_rules,
            prompt_overrides=prompt_overrides,
            retrieval_rules=retrieval_rules,
            parse_rules=parse_rules,
        )

        profile = IndustryProfile(
            id=uuid7(),
            tenant_id=claims.tenant_id,
            code=payload.code,
            name=payload.name or f"{base.name}（自定义）",
            parse_rules=parse_rules or {},
            chunk_rules=chunk_rules or {},
            metadata_schema=metadata_schema or {},
            prompt_overrides=prompt_overrides or {},
            retrieval_rules=retrieval_rules or {},
            is_builtin=False,
        )
        await self._repo.add_profile(profile)
        return IndustryProfileOut.model_validate(profile)

    async def update_profile(
        self,
        claims: TokenClaims,
        profile_id: uuid.UUID,
        payload: IndustryProfileUpdate,
    ) -> IndustryProfileOut:
        profile = await self._repo.get_profile(claims.tenant_id, profile_id)
        if profile is None:
            raise NotFound()
        if profile.is_builtin or profile.tenant_id is None:
            raise UnprocessableState("内置模板不可修改，请先派生", code="builtin_immutable")
        if profile.tenant_id != claims.tenant_id:
            raise NotFound()

        data = payload.model_dump(exclude_unset=True)
        if "name" in data and data["name"] is not None:
            profile.name = data["name"]
        for field in (
            "chunk_rules",
            "prompt_overrides",
            "retrieval_rules",
            "parse_rules",
            "metadata_schema",
        ):
            if field in data and data[field] is not None:
                setattr(profile, field, copy.deepcopy(data[field]))

        _validate_profile_rules(
            chunk_rules=profile.chunk_rules,
            prompt_overrides=profile.prompt_overrides,
            retrieval_rules=profile.retrieval_rules,
            parse_rules=profile.parse_rules,
        )
        await self._repo._session.flush()
        return IndustryProfileOut.model_validate(profile)

    async def delete_profile(self, claims: TokenClaims, profile_id: uuid.UUID) -> None:
        row = await self._repo.get_profile(claims.tenant_id, profile_id)
        if row is None or row.deleted_at is not None:
            raise NotFound("行业模板不存在")
        if row.is_builtin or row.tenant_id is None:
            raise UnprocessableState("内置模板不可删除", code="builtin_immutable")
        if row.tenant_id != claims.tenant_id:
            raise NotFound("行业模板不存在")
        in_use = await self._repo.count_kbs_with_profile(profile_id)
        if in_use:
            raise Conflict("仍有知识库绑定该模板", code="profile_in_use")
        row.deleted_at = datetime.now(UTC)
        await self._repo._session.flush()

    async def restore_profile(
        self, claims: TokenClaims, profile_id: uuid.UUID
    ) -> IndustryProfileOut:
        row = await self._repo.get_tenant_profile_any(claims.tenant_id, profile_id)
        if row is None or row.deleted_at is None:
            raise NotFound("已删除的行业模板不存在")
        if await self._repo.tenant_profile_code_exists(claims.tenant_id, row.code):
            raise Conflict("本租户已存在相同 code", code="profile_code_in_use")
        row.deleted_at = None
        await self._repo._session.flush()
        return IndustryProfileOut.model_validate(row)

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
        if payload.profile_code is not None:
            profile = await self._repo.get_profile_by_code(claims.tenant_id, payload.profile_code)
            if profile is None:
                raise UnprocessableState("行业模板不存在", code="profile_not_found")
            kb.profile_id = profile.id
        await self._repo._session.flush()
        return KnowledgeBaseOut.model_validate(kb)

    async def delete_knowledge_base(self, claims: TokenClaims, kb_id: uuid.UUID) -> None:
        kb = await self._require_kb(claims, kb_id, PERM_MANAGE)
        name = kb.name
        kb.deleted_at = datetime.now(UTC)
        await AuditService(self._repo._session).record(
            tenant_id=claims.tenant_id,
            actor_id=claims.user_id,
            action="knowledge_base.delete",
            target_type="knowledge_base",
            target_id=kb_id,
            payload={"name": name},
        )

    async def list_grants(self, claims: TokenClaims, kb_id: uuid.UUID) -> list[GrantOut]:
        await self._require_kb(claims, kb_id, PERM_MANAGE)
        rows = await self._repo.list_grants(claims.tenant_id, kb_id)
        return [await self._grant_out(r) for r in rows]

    async def upsert_grant(
        self,
        claims: TokenClaims,
        kb_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: GrantUpsert,
    ) -> GrantOut:
        await self._require_kb(claims, kb_id, PERM_MANAGE)
        from app.modules.identity.repository import IdentityRepository

        membership = await IdentityRepository(self._repo._session).get_membership(
            user_id, claims.tenant_id
        )
        if membership is None:
            raise NotFound("用户不是本租户成员")

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
            await AuditService(self._repo._session).record(
                tenant_id=claims.tenant_id,
                actor_id=claims.user_id,
                action="kb_grant.create",
                target_type="kb_grant",
                target_id=row.id,
                payload={
                    "grant_id": str(row.id),
                    "kb_id": str(kb_id),
                    "grantee_user_id": str(user_id),
                    "permission": payload.permission,
                },
            )
        else:
            old_perm = existing.permission
            existing.permission = payload.permission
            row = existing
            await self._repo._session.flush()
            await AuditService(self._repo._session).record(
                tenant_id=claims.tenant_id,
                actor_id=claims.user_id,
                action="kb_grant.update",
                target_type="kb_grant",
                target_id=row.id,
                payload={
                    "grant_id": str(row.id),
                    "kb_id": str(kb_id),
                    "changes": {"permission": {"from": old_perm, "to": payload.permission}},
                },
            )
        return await self._grant_out(row)

    async def delete_grant(self, claims: TokenClaims, kb_id: uuid.UUID, user_id: uuid.UUID) -> None:
        await self._require_kb(claims, kb_id, PERM_MANAGE)
        existing = await self._repo.get_grant(claims.tenant_id, kb_id, user_id)
        if existing is None:
            raise NotFound("授权不存在")
        grant_id = existing.id
        await self._repo.delete_grant(existing)
        await AuditService(self._repo._session).record(
            tenant_id=claims.tenant_id,
            actor_id=claims.user_id,
            action="kb_grant.delete",
            target_type="kb_grant",
            target_id=grant_id,
            payload={"grant_id": str(grant_id), "kb_id": str(kb_id)},
        )

    async def _grant_out(self, row: KbGrant) -> GrantOut:
        from app.modules.identity.repository import IdentityRepository

        user = await IdentityRepository(self._repo._session).get_user(row.user_id)
        base = GrantOut.model_validate(row)
        if user is None:
            return base
        return base.model_copy(update={"email": user.email, "display_name": user.display_name})

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

        from app.modules.knowledge.metadata_validate import validate_document_metadata
        from app.modules.profile.service import resolve_effective_profile

        effective = await resolve_effective_profile(self._repo._session, kb.id)
        validate_document_metadata(payload.metadata or {}, effective.metadata_schema)

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
        from app.modules.ingestion.parsers.dispatch import resolve_content_type

        mime = resolve_content_type(content_type, filename)
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

    async def list_pages(self, claims: TokenClaims, doc_id: uuid.UUID) -> list[DocumentPageOut]:
        await self._require_doc(claims, doc_id, PERM_READ)
        rows = await self._repo.list_pages(claims.tenant_id, doc_id)
        return [
            DocumentPageOut(page_no=p.page_no, plain_text=p.plain_text, source=p.source)
            for p in rows
        ]

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
