"""知识库与文档 HTTP 接口。"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.modules.identity.models import ROLE_ADMIN
from app.modules.ingestion.events import iter_document_events
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
from app.modules.knowledge.service import KnowledgeService
from app.platform.deps import ClaimsDep, SettingsDep, TenantSessionDep, require_role

router = APIRouter(tags=["knowledge"])


def _service(session: TenantSessionDep, settings: SettingsDep) -> KnowledgeService:
    return KnowledgeService(KnowledgeRepository(session), settings)


ServiceDep = Depends(_service)


@router.get("/industry-profiles", response_model=list[IndustryProfileOut])
async def list_profiles(
    claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> list[IndustryProfileOut]:
    return await service.list_profiles(claims.tenant_id)


@router.post(
    "/industry-profiles",
    response_model=IndustryProfileOut,
    status_code=201,
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def create_profile(
    payload: IndustryProfileCreate,
    claims: ClaimsDep,
    service: KnowledgeService = ServiceDep,
) -> IndustryProfileOut:
    return await service.create_profile(claims, payload)


@router.patch(
    "/industry-profiles/{profile_id}",
    response_model=IndustryProfileOut,
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def update_profile(
    profile_id: uuid.UUID,
    payload: IndustryProfileUpdate,
    claims: ClaimsDep,
    service: KnowledgeService = ServiceDep,
) -> IndustryProfileOut:
    return await service.update_profile(claims, profile_id, payload)


@router.delete(
    "/industry-profiles/{profile_id}",
    status_code=204,
    dependencies=[Depends(require_role(ROLE_ADMIN))],
)
async def delete_profile(
    profile_id: uuid.UUID,
    claims: ClaimsDep,
    service: KnowledgeService = ServiceDep,
) -> None:
    await service.delete_profile(claims, profile_id)


@router.get("/knowledge-bases", response_model=list[KnowledgeBaseOut])
async def list_knowledge_bases(
    claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> list[KnowledgeBaseOut]:
    return await service.list_knowledge_bases(claims)


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
    return await service.get_knowledge_base(claims, kb_id)


@router.patch("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseOut)
async def update_knowledge_base(
    kb_id: uuid.UUID,
    payload: KnowledgeBaseUpdate,
    claims: ClaimsDep,
    service: KnowledgeService = ServiceDep,
) -> KnowledgeBaseOut:
    return await service.update_knowledge_base(claims, kb_id, payload)


@router.delete("/knowledge-bases/{kb_id}", status_code=204)
async def delete_knowledge_base(
    kb_id: uuid.UUID, claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> None:
    await service.delete_knowledge_base(claims, kb_id)


@router.get("/knowledge-bases/{kb_id}/grants", response_model=list[GrantOut])
async def list_grants(
    kb_id: uuid.UUID, claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> list[GrantOut]:
    return await service.list_grants(claims, kb_id)


@router.put("/knowledge-bases/{kb_id}/grants/{user_id}", response_model=GrantOut)
async def upsert_grant(
    kb_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: GrantUpsert,
    claims: ClaimsDep,
    service: KnowledgeService = ServiceDep,
) -> GrantOut:
    return await service.upsert_grant(claims, kb_id, user_id, payload)


@router.delete("/knowledge-bases/{kb_id}/grants/{user_id}", status_code=204)
async def delete_grant(
    kb_id: uuid.UUID,
    user_id: uuid.UUID,
    claims: ClaimsDep,
    service: KnowledgeService = ServiceDep,
) -> None:
    await service.delete_grant(claims, kb_id, user_id)


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
    return await service.list_documents(claims, kb_id)


@router.get("/documents/{doc_id}", response_model=DocumentOut)
async def get_document(
    doc_id: uuid.UUID, claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> DocumentOut:
    return await service.get_document(claims, doc_id)


@router.delete("/documents/{doc_id}", status_code=204)
async def delete_document(
    doc_id: uuid.UUID, claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> None:
    await service.delete_document(claims, doc_id)


@router.post("/documents/{doc_id}/reingest", response_model=DocumentCreated, status_code=202)
async def reingest(
    doc_id: uuid.UUID, claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> DocumentCreated:
    return await service.reingest(claims, doc_id)


@router.get("/documents/{doc_id}/preview-url", response_model=PreviewUrlOut)
async def preview_url(
    doc_id: uuid.UUID, claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> PreviewUrlOut:
    return await service.preview_url(claims, doc_id)


@router.get("/documents/{doc_id}/pages", response_model=list[DocumentPageOut])
async def list_pages(
    doc_id: uuid.UUID, claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> list[DocumentPageOut]:
    return await service.list_pages(claims, doc_id)


@router.get("/documents/{doc_id}/events")
async def document_events(
    doc_id: uuid.UUID,
    claims: ClaimsDep,
    settings: SettingsDep,
    service: KnowledgeService = ServiceDep,
) -> StreamingResponse:
    """摄取进度 SSE（详情页用；列表页继续轮询）。"""

    async def _gen() -> AsyncIterator[str]:
        async for chunk in iter_document_events(
            service=service,
            claims=claims,
            settings=settings,
            doc_id=doc_id,
        ):
            yield chunk

    return StreamingResponse(
        _gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/documents/{doc_id}/chunks", response_model=list[ChunkOut])
async def list_chunks(
    doc_id: uuid.UUID, claims: ClaimsDep, service: KnowledgeService = ServiceDep
) -> list[ChunkOut]:
    return await service.list_chunks(claims, doc_id)
