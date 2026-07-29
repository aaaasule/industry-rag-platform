"""会话与问答 HTTP 接口。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.modules.chat.repository import ChatRepository
from app.modules.chat.schemas import (
    ChatCompletionRequest,
    ConversationCreate,
    ConversationOut,
    MessageOut,
)
from app.modules.chat.service import ChatService
from app.modules.retrieval.repository import RetrievalRepository
from app.modules.retrieval.service import RetrievalService
from app.platform.deps import ClaimsDep, EmbeddingDep, LLMDep, TenantSessionDep

router = APIRouter(tags=["chat"])


def _service(session: TenantSessionDep, embedding: EmbeddingDep, llm: LLMDep) -> ChatService:
    retrieval = RetrievalService(session, embedding, repo=RetrievalRepository(session))
    return ChatService(session, retrieval, llm, repo=ChatRepository(session))


ServiceDep = Depends(_service)


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    claims: ClaimsDep, service: ChatService = ServiceDep
) -> list[ConversationOut]:
    return await service.list_conversations(claims)


@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation(
    payload: ConversationCreate,
    claims: ClaimsDep,
    service: ChatService = ServiceDep,
) -> ConversationOut:
    return await service.create_conversation(claims, payload)


@router.delete("/conversations/{conv_id}", status_code=204)
async def delete_conversation(
    conv_id: uuid.UUID, claims: ClaimsDep, service: ChatService = ServiceDep
) -> None:
    await service.delete_conversation(claims, conv_id)


@router.get("/conversations/{conv_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conv_id: uuid.UUID, claims: ClaimsDep, service: ChatService = ServiceDep
) -> list[MessageOut]:
    return await service.list_messages(claims, conv_id)


@router.post("/chat/completions")
async def chat_completions(
    payload: ChatCompletionRequest,
    claims: ClaimsDep,
    service: ChatService = ServiceDep,
) -> StreamingResponse:
    temperature = float(payload.options.get("temperature", 0.1))
    gen = service.stream_completion(
        claims,
        message=payload.message,
        conversation_id=payload.conversation_id,
        kb_ids=payload.kb_ids,
        temperature=temperature,
    )
    return StreamingResponse(gen, media_type="text/event-stream")
