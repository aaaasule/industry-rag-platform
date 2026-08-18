"""会话数据访问。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.chat.models import Conversation, Message, MessageFeedback


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_conversations(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(
                Conversation.tenant_id == tenant_id,
                Conversation.user_id == user_id,
                Conversation.deleted_at.is_(None),
            )
            .order_by(Conversation.updated_at.desc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_conversation(
        self, tenant_id: uuid.UUID, user_id: uuid.UUID, conv_id: uuid.UUID
    ) -> Conversation | None:
        stmt = select(Conversation).where(
            Conversation.id == conv_id,
            Conversation.tenant_id == tenant_id,
            Conversation.user_id == user_id,
            Conversation.deleted_at.is_(None),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add_conversation(self, conv: Conversation) -> Conversation:
        self._session.add(conv)
        await self._session.flush()
        return conv

    async def soft_delete(self, conv: Conversation) -> None:
        conv.deleted_at = datetime.now(UTC)

    async def list_messages(
        self, tenant_id: uuid.UUID, conversation_id: uuid.UUID
    ) -> list[Message]:
        stmt = (
            select(Message)
            .options(selectinload(Message.citations), selectinload(Message.feedbacks))
            .where(
                Message.tenant_id == tenant_id,
                Message.conversation_id == conversation_id,
            )
            .order_by(Message.created_at.asc())
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def add_message(self, msg: Message) -> Message:
        self._session.add(msg)
        await self._session.flush()
        return msg

    async def get_message(self, tenant_id: uuid.UUID, message_id: uuid.UUID) -> Message | None:
        stmt = (
            select(Message)
            .options(
                selectinload(Message.conversation),
                selectinload(Message.citations),
                selectinload(Message.feedbacks),
            )
            .where(Message.id == message_id, Message.tenant_id == tenant_id)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def get_feedback(
        self, tenant_id: uuid.UUID, message_id: uuid.UUID, user_id: uuid.UUID
    ) -> MessageFeedback | None:
        stmt = select(MessageFeedback).where(
            MessageFeedback.tenant_id == tenant_id,
            MessageFeedback.message_id == message_id,
            MessageFeedback.user_id == user_id,
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def add_feedback(self, row: MessageFeedback) -> MessageFeedback:
        self._session.add(row)
        await self._session.flush()
        return row
