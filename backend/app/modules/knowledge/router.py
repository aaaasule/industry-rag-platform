"""知识库与文档 HTTP 接口。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.modules.knowledge.repository import KnowledgeRepository
from app.modules.knowledge.schemas import (
    DocumentCreated,
    DocumentOut,
    DocumentRegisterRequest,
    IndustryProfileOut,
    KnowledgeBaseCreate,
    KnowledgeBaseOut,
    KnowledgeBaseUpdate,
    PreviewUrlOut,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.modules.knowledge.service import KnowledgeService
from app.platform.deps import ClaimsDep, SettingsDep, TenantSessionDep

router = APIRouter(tags=["knowledge"])


def _service(session: TenantSessionDep, settings: SettingsDep) -> KnowledgeService:
    return KnowledgeService(KnowledgeRepository(session), settings)


ServiceDep = Depends(_service)


@router.get("/industry-profiles", response_model=list[IndustryProfileOut])
async def list_profiles(
    claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> list[IndustryProfileOut]:
    return await service.list_profiles(claims.tenant_id)


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseOut])
async def list_knowledge_bases(
    claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> list[KnowledgeBaseOut]:
    return await service.list_knowledge_bases(claims.tenant_id)


@router.post("/knowledge-bases", response_model=KnowledgeBaseOut, status_code=201)
async def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    claims: ClaimsDep,
    service: KnowledgeService = ServiceDep,
) -> KnowledgeBaseOut:
    return await service.create_knowledge_base(claims, payload)


@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseOut)
async def get_knowledge_base(
    kb_id: uuid.UUID, claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> KnowledgeBaseOut:
    return await service.get_knowledge_base(claims.tenant_id, kb_id)


@router.patch("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseOut)
async def update_knowledge_base(
    kb_id: uuid.UUID,
    payload: KnowledgeBaseUpdate,
    claims: ClaimsDep,
    service: KnowledgeService = ServiceDep,
) -> KnowledgeBaseOut:
    return await service.update_knowledge_base(claims.tenant_id, kb_id, payload)


@router.delete("/knowledge-bases/{kb_id}", status_code=204)
async def delete_knowledge_base(
    kb_id: uuid.UUID, claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> None:
    await service.delete_knowledge_base(claims.tenant_id, kb_id)


@router.post(
    "/knowledge-bases/{kb_id}/documents/upload-url",
    response_model=UploadUrlResponse,
)
async def create_upload_url(
    kb_id: uuid.UUID,
    payload: UploadUrlRequest,
    claims: ClaimsDep,
    service: KnowledgeService = ServiceDep,
) -> UploadUrlResponse:
    return await service.create_upload_url(claims, kb_id, payload)


@router.post(
    "/knowledge-bases/{kb_id}/documents",
    response_model=DocumentCreated,
    status_code=202,
)
async def register_document(
    kb_id: uuid.UUID,
    payload: DocumentRegisterRequest,
    claims: ClaimsDep,
    service: KnowledgeService = ServiceDep,
) -> DocumentCreated:
    return await service.register_document(claims, kb_id, payload)


@router.post(
    "/knowledge-bases/{kb_id}/documents/upload",
    response_model=DocumentCreated,
    status_code=202,
)
async def upload_document(
    kb_id: uuid.UUID,
    claims: ClaimsDep,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    service: KnowledgeService = ServiceDep,
) -> DocumentCreated:
    data = await file.read()
    return await service.upload_document(
        claims,
        kb_id,
        filename=file.filename or "upload.bin",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        title=title,
    )


@router.get("/knowledge-bases/{kb_id}/documents", response_model=list[DocumentOut])
async def list_documents(
    kb_id: uuid.UUID, claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> list[DocumentOut]:
    return await service.list_documents(claims.tenant_id, kb_id)


@router.get("/documents/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: uuid.UUID, claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> DocumentOut:
    return await service.get_document(claims.tenant_id, doc_id)


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(
    doc_id: uuid.UUID, claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> None:
    await service.delete_document(claims.tenant_id, doc_id)


@router.post("/documents/{doc_id}/reingest", response_model=DocumentCreated, status_code=202)
async def reingest(
    doc_id: uuid.UUID, claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> DocumentCreated:
    return await service.reingest(claims.tenant_id, doc_id)


@router.get("/documents/{doc_id}/preview-url", response_model=PreviewUrlOut)
async def preview_url(
    doc_id: uuid.UUID, claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> PreviewUrlOut:
    return await service.preview_url(claims.tenant_id, doc_id)
