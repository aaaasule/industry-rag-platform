"""会话与流式问答编排。"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.citations import validate_citations
from app.modules.chat.models import (
    MSG_COMPLETED,
    MSG_FAILED,
    MSG_STREAMING,
    ROLE_ASSISTANT,
    ROLE_USER,
    Citation,
    Conversation,
    Message,
    MessageFeedback,
)
from app.modules.chat.prompts import build_messages
from app.modules.chat.refuse import should_refuse
from app.modules.chat.repository import ChatRepository
from app.modules.chat.rewrite import resolve_query
from app.modules.chat.schemas import (
    CitationOut,
    ConversationCreate,
    ConversationOut,
    FeedbackCreate,
    FeedbackOut,
    MessageOut,
)
from app.modules.chat.sse import sse_event
from app.modules.identity.permissions import PERM_READ, visible_kb_ids
from app.modules.profile.service import resolve_for_kb_ids, resolve_rerank_enabled
from app.modules.retrieval.base import SearchOptions
from app.modules.retrieval.expand import load_document_titles
from app.modules.retrieval.service import RetrievalService
from app.platform.config import get_settings
from app.platform.db import set_rls_context
from app.platform.errors import AppError, Forbidden, NotFound, UnprocessableState
from app.platform.ids import uuid7
from app.platform.llm.base import LLMProvider
from app.platform.llm.base import Message as LLMMessage
from app.platform.security import TokenClaims


class ChatService:
    def __init__(
        self,
        session: AsyncSession,
        retrieval: RetrievalService,
        llm: LLMProvider,
        *,
        repo: ChatRepository | None = None,
    ) -> None:
        self._session = session
        self._retrieval = retrieval
        self._llm = llm
        self._repo = repo or ChatRepository(session)

    async def _commit_keep_rls(self, claims: TokenClaims) -> None:
        """中途 commit 会结束事务，SET LOCAL 的 RLS 变量随之失效，必须重写。"""
        await self._session.commit()
        await set_rls_context(self._session, tenant_id=claims.tenant_id, user_id=claims.user_id)

    async def list_conversations(self, claims: TokenClaims) -> list[ConversationOut]:
        rows = await self._repo.list_conversations(claims.tenant_id, claims.user_id)
        return [ConversationOut.model_validate(r) for r in rows]

    async def create_conversation(
        self, claims: TokenClaims, payload: ConversationCreate
    ) -> ConversationOut:
        await self._assert_kb_readable(claims, payload.kb_ids)
        conv = Conversation(
            id=uuid7(),
            tenant_id=claims.tenant_id,
            user_id=claims.user_id,
            kb_ids=payload.kb_ids,
            title=payload.title,
        )
        await self._repo.add_conversation(conv)
        return ConversationOut.model_validate(conv)

    async def delete_conversation(self, claims: TokenClaims, conv_id: uuid.UUID) -> None:
        conv = await self._repo.get_conversation(claims.tenant_id, claims.user_id, conv_id)
        if conv is None:
            raise NotFound("会话不存在")
        await self._repo.soft_delete(conv)

    async def list_messages(self, claims: TokenClaims, conv_id: uuid.UUID) -> list[MessageOut]:
        conv = await self._repo.get_conversation(claims.tenant_id, claims.user_id, conv_id)
        if conv is None:
            raise NotFound("会话不存在")
        rows = await self._repo.list_messages(claims.tenant_id, conv_id)
        doc_ids = [c.document_id for m in rows for c in m.citations]
        titles = await load_document_titles(self._session, doc_ids)
        return [self._to_message_out(m, titles, claims.user_id) for m in rows]

    async def upsert_feedback(
        self, claims: TokenClaims, message_id: uuid.UUID, payload: FeedbackCreate
    ) -> FeedbackOut:
        msg = await self._repo.get_message(claims.tenant_id, message_id)
        if msg is None:
            raise NotFound("消息不存在")
        conv = msg.conversation
        if (
            conv is None
            or conv.user_id != claims.user_id
            or conv.deleted_at is not None
            or conv.tenant_id != claims.tenant_id
        ):
            raise NotFound("消息不存在")
        if msg.role != ROLE_ASSISTANT:
            raise UnprocessableState("只能评价助手消息")
        if msg.status != MSG_COMPLETED:
            raise UnprocessableState("只能评价已完成的回答")
        if payload.rating == "down" and payload.reason is None and not payload.comment:
            # 允许无原因的踩，但前端默认会带 reason
            pass

        existing = await self._repo.get_feedback(claims.tenant_id, message_id, claims.user_id)
        now = datetime.now(UTC)
        if existing is None:
            row = MessageFeedback(
                id=uuid7(),
                tenant_id=claims.tenant_id,
                message_id=message_id,
                user_id=claims.user_id,
                rating=payload.rating,
                reason=payload.reason,
                comment=payload.comment,
            )
            await self._repo.add_feedback(row)
        else:
            existing.rating = payload.rating
            existing.reason = payload.reason
            existing.comment = payload.comment
            existing.updated_at = now
            row = existing
        await self._session.flush()
        return FeedbackOut.model_validate(row)

    @staticmethod
    def _to_message_out(
        msg: Message, titles: dict[uuid.UUID, str], user_id: uuid.UUID
    ) -> MessageOut:
        used: list[int] = []
        took_ms: int | None = None
        if isinstance(msg.retrieval_meta, dict):
            raw = msg.retrieval_meta.get("used_citations")
            if isinstance(raw, list):
                for x in raw:
                    if isinstance(x, (int, float)) or (isinstance(x, str) and x.isdigit()):
                        used.append(int(x))
            raw_took = msg.retrieval_meta.get("took_ms")
            if isinstance(raw_took, (int, float)):
                took_ms = int(raw_took)

        feedback = None
        for fb in msg.feedbacks or []:
            if fb.user_id == user_id:
                feedback = FeedbackOut.model_validate(fb)
                break

        citations = [
            CitationOut(
                index_no=c.index_no,
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                document_title=titles.get(c.document_id, ""),
                quote=c.quote,
                page_start=c.page_start,
                bboxes=list(c.bboxes or []),
                score=c.score,
            )
            for c in sorted(msg.citations, key=lambda x: x.index_no)
        ]
        token_usage = msg.token_usage if isinstance(msg.token_usage, dict) else None
        return MessageOut(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            status=msg.status,
            citations=citations,
            used_citations=used,
            feedback=feedback,
            token_usage=token_usage,
            took_ms=took_ms,
            created_at=msg.created_at,
        )

    async def _assert_kb_readable(self, claims: TokenClaims, kb_ids: list[uuid.UUID]) -> None:
        visible = set(
            await visible_kb_ids(
                self._session,
                tenant_id=claims.tenant_id,
                user_id=claims.user_id,
                role=claims.role,
                permission=PERM_READ,
            )
        )
        unknown = [i for i in kb_ids if i not in visible]
        if not unknown:
            return
        # 同租户存在但不可见 → 403；否则 404
        from app.modules.identity.permissions import kb_exists_in_tenant

        for kid in unknown:
            if await kb_exists_in_tenant(self._session, tenant_id=claims.tenant_id, kb_id=kid):
                raise Forbidden("没有权限访问所选知识库")
        raise NotFound("知识库不存在或不可见")

    async def stream_completion(
        self,
        claims: TokenClaims,
        *,
        message: str,
        conversation_id: uuid.UUID | None,
        kb_ids: list[uuid.UUID] | None,
        temperature: float = 0.1,
    ) -> AsyncIterator[bytes]:
        if conversation_id is None:
            if not kb_ids:
                raise UnprocessableState("新建会话必须提供 kb_ids")
            await self._assert_kb_readable(claims, kb_ids)
            conv = Conversation(
                id=uuid7(),
                tenant_id=claims.tenant_id,
                user_id=claims.user_id,
                kb_ids=kb_ids,
                title=message[:40] or "新会话",
            )
            await self._repo.add_conversation(conv)
        else:
            found = await self._repo.get_conversation(
                claims.tenant_id, claims.user_id, conversation_id
            )
            if found is None:
                raise NotFound("会话不存在")
            conv = found
            if kb_ids:
                await self._assert_kb_readable(claims, kb_ids)
                conv.kb_ids = kb_ids

        user_msg = Message(
            id=uuid7(),
            tenant_id=claims.tenant_id,
            conversation_id=conv.id,
            role=ROLE_USER,
            content=message,
            status=MSG_COMPLETED,
        )
        await self._repo.add_message(user_msg)

        asst = Message(
            id=uuid7(),
            tenant_id=claims.tenant_id,
            conversation_id=conv.id,
            role=ROLE_ASSISTANT,
            content="",
            status=MSG_STREAMING,
            model=getattr(self._llm, "model", None) or self._llm.name,
        )
        await self._repo.add_message(asst)
        await self._commit_keep_rls(claims)

        yield sse_event(
            "message_created",
            {"message_id": str(asst.id), "conversation_id": str(conv.id)},
        )
        async for chunk in self._stream_answer(
            claims, conv=conv, asst=asst, query=message, temperature=temperature
        ):
            yield chunk

    async def ensure_regenerable(self, claims: TokenClaims, message_id: uuid.UUID) -> None:
        await self._load_regenerate_context(claims, message_id)

    async def _load_regenerate_context(
        self, claims: TokenClaims, message_id: uuid.UUID
    ) -> tuple[Message, Conversation, Message]:
        asst = await self._repo.get_message(claims.tenant_id, message_id)
        if asst is None:
            raise NotFound("消息不存在")
        conv = asst.conversation
        if (
            conv is None
            or conv.user_id != claims.user_id
            or conv.deleted_at is not None
            or conv.tenant_id != claims.tenant_id
        ):
            raise NotFound("消息不存在")
        if asst.role != ROLE_ASSISTANT:
            raise UnprocessableState("只能重新生成助手消息")
        if asst.status == MSG_STREAMING:
            raise UnprocessableState("回答正在生成中")

        history = await self._repo.list_messages(claims.tenant_id, conv.id)
        if not history or history[-1].id != asst.id:
            raise UnprocessableState("只能重新生成会话中最后一条消息")
        user_msg = next((m for m in reversed(history[:-1]) if m.role == ROLE_USER), None)
        if user_msg is None or not user_msg.content.strip():
            raise UnprocessableState("找不到对应的用户问题")
        return asst, conv, user_msg

    async def stream_regenerate(
        self,
        claims: TokenClaims,
        *,
        message_id: uuid.UUID,
        temperature: float = 0.1,
    ) -> AsyncIterator[bytes]:
        asst, conv, user_msg = await self._load_regenerate_context(claims, message_id)

        asst.citations.clear()
        asst.feedbacks.clear()
        asst.content = ""
        asst.status = MSG_STREAMING
        asst.retrieval_meta = None
        asst.token_usage = None
        asst.model = getattr(self._llm, "model", None) or self._llm.name
        await self._commit_keep_rls(claims)

        yield sse_event(
            "message_created",
            {"message_id": str(asst.id), "conversation_id": str(conv.id)},
        )
        async for chunk in self._stream_answer(
            claims, conv=conv, asst=asst, query=user_msg.content, temperature=temperature
        ):
            yield chunk

    async def _stream_answer(
        self,
        claims: TokenClaims,
        *,
        conv: Conversation,
        asst: Message,
        query: str,
        temperature: float,
    ) -> AsyncIterator[bytes]:
        settings = get_settings()
        effective = await resolve_for_kb_ids(self._session, list(conv.kb_ids))
        rerank = resolve_rerank_enabled(
            effective.retrieval_rules, env_default=settings.effective_rerank_default
        )

        t0 = time.perf_counter()
        rows = await self._repo.list_messages(claims.tenant_id, conv.id)
        prior = [m for m in rows if m.status == MSG_COMPLETED and (m.content or "").strip()]
        # 当前轮用户消息已落库为 completed，排除后再取最近 4 条
        if prior and prior[-1].role == ROLE_USER:
            prior = prior[:-1]
        history = [(m.role, m.content) for m in prior[-4:]]
        search_query = await resolve_query(self._llm, history=history, current=query)

        try:
            search = await self._retrieval.search(
                tenant_id=claims.tenant_id,
                user_id=claims.user_id,
                role=claims.role,
                query=search_query,
                kb_ids=list(conv.kb_ids),
                top_k=effective.retrieval_rules.top_k,
                options=SearchOptions(
                    rerank=rerank,
                    query_expand=effective.retrieval_rules.query_expand,
                ),
                dictionary=effective.parse_rules.get("dictionary"),
                synonyms=effective.parse_rules.get("synonyms"),
            )
        except AppError as exc:
            asst.content = str(exc.message)
            asst.status = MSG_FAILED
            await self._commit_keep_rls(claims)
            yield sse_event("error", {"code": exc.code, "message": exc.message})
            return

        took_ms = int((time.perf_counter() - t0) * 1000)
        yield sse_event(
            "retrieval",
            {
                "rewritten_query": search.rewritten_query,
                "hit_count": len(search.hits),
                "took_ms": took_ms,
            },
        )

        reason = should_refuse(search.hits)
        if reason:
            text = "未找到足够相关的资料，请换一种问法或补充上传文档。"
            total_ms = int((time.perf_counter() - t0) * 1000)
            asst.content = text
            asst.status = MSG_COMPLETED
            asst.retrieval_meta = {
                "rewritten_query": search.rewritten_query,
                "hit_count": len(search.hits),
                "refuse_reason": reason,
                "took_ms": total_ms,
            }
            await self._commit_keep_rls(claims)
            yield sse_event(
                "no_answer",
                {
                    "reason": reason,
                    "suggestions": ["缩小知识库范围", "换用文档中的术语提问"],
                    "took_ms": total_ms,
                },
            )
            return

        citations_payload = []
        for i, h in enumerate(search.hits, start=1):
            quote = h.content[:280]
            score = float(h.scores.get("rrf") or 0.0)
            self._session.add(
                Citation(
                    id=uuid7(),
                    tenant_id=claims.tenant_id,
                    message_id=asst.id,
                    chunk_id=h.chunk_id,
                    document_id=h.document_id,
                    index_no=i,
                    quote=quote,
                    page_start=h.page_start,
                    bboxes=h.bboxes,
                    score=score,
                )
            )
            citations_payload.append(
                {
                    "index_no": i,
                    "document_id": str(h.document_id),
                    "document_title": h.document_title,
                    "page_start": h.page_start,
                    "bboxes": h.bboxes,
                    "quote": quote,
                    "chunk_id": str(h.chunk_id),
                    "score": score,
                }
            )
        await self._session.flush()
        yield sse_event("citations", {"citations": citations_payload})

        llm_msgs = [
            LLMMessage(role=m["role"], content=m["content"])  # type: ignore[arg-type]
            for m in build_messages(
                query,
                search.hits,
                system_override=effective.prompt_overrides.system,
            )
        ]
        buf: list[str] = []
        usage = None
        llm_t0 = time.perf_counter()
        try:
            async for delta in self._llm.stream(llm_msgs, temperature=temperature):
                if delta.content:
                    buf.append(delta.content)
                    yield sse_event("delta", {"text": delta.content})
                if delta.usage is not None:
                    usage = delta.usage
            raw = "".join(buf)
            cleaned, used = validate_citations(raw, max_index=len(search.hits))
            total_ms = int((time.perf_counter() - t0) * 1000)
            asst.content = cleaned
            asst.status = MSG_COMPLETED
            asst.retrieval_meta = {
                "rewritten_query": search.rewritten_query,
                "hit_count": len(search.hits),
                "used_citations": used,
                "took_ms": total_ms,
            }
            if usage is not None:
                asst.token_usage = {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                }
            conv.updated_at = datetime.now(UTC)
            await self._commit_keep_rls(claims)
            await self._record_chat_usage(
                claims,
                latency_ms=int((time.perf_counter() - llm_t0) * 1000),
                success=True,
                prompt_tokens=int((usage.prompt_tokens if usage else 0) or 0),
                completion_tokens=int((usage.completion_tokens if usage else 0) or 0),
                kb_id=next(iter(conv.kb_ids)) if conv.kb_ids else None,
            )
            yield sse_event(
                "done",
                {
                    "finish_reason": "stop",
                    "used_citations": used,
                    "usage": asst.token_usage or {},
                    "took_ms": total_ms,
                },
            )
        except Exception as exc:
            asst.content = "".join(buf)
            asst.status = MSG_FAILED
            await self._commit_keep_rls(claims)
            await self._record_chat_usage(
                claims,
                latency_ms=int((time.perf_counter() - llm_t0) * 1000),
                success=False,
                prompt_tokens=int((usage.prompt_tokens if usage else 0) or 0),
                completion_tokens=int((usage.completion_tokens if usage else 0) or 0),
                kb_id=next(iter(conv.kb_ids)) if conv.kb_ids else None,
                error_code="stream_failed",
            )
            yield sse_event("error", {"code": "stream_failed", "message": str(exc)})

    async def _record_chat_usage(
        self,
        claims: TokenClaims,
        *,
        latency_ms: int,
        success: bool,
        prompt_tokens: int,
        completion_tokens: int,
        kb_id: uuid.UUID | None,
        error_code: str | None = None,
    ) -> None:
        from app.modules.modelops.usage_recorder import UsageRecorder, resolve_usage_route

        conn_id, provider_type, model = await resolve_usage_route(
            self._session, claims.tenant_id, "chat"
        )
        await UsageRecorder.record(
            tenant_id=claims.tenant_id,
            user_id=claims.user_id,
            connection_id=conn_id,
            kb_id=kb_id,
            purpose="chat",
            provider_type=provider_type,
            model=model or getattr(self._llm, "model", None) or self._llm.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            success=success,
            error_code=error_code,
        )
