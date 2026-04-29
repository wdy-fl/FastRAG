from __future__ import annotations
from uuid import uuid4
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastrag.db.models.conversation import (
    ConversationORM, MessageORM, ConversationSummaryORM
)


class ConversationRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_recent_messages(
        self, conversation_id: str, limit: int
    ) -> list[MessageORM]:
        stmt = (
            select(MessageORM)
            .where(MessageORM.conversation_id == conversation_id)
            .order_by(MessageORM.seq.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        return list(reversed(rows))

    async def save_message(
        self, conversation_id: str, role: str, content: str
    ) -> MessageORM:
        count = await self.count_messages(conversation_id)
        msg = MessageORM(
            id=str(uuid4()),
            conversation_id=conversation_id,
            seq=count + 1,
            role=role,
            content=content,
        )
        self._session.add(msg)
        await self._session.commit()
        return msg

    async def get_summary(
        self, conversation_id: str
    ) -> ConversationSummaryORM | None:
        stmt = select(ConversationSummaryORM).where(
            ConversationSummaryORM.conversation_id == conversation_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_summary(
        self, conversation_id: str, content: str, up_to_seq: int
    ) -> None:
        existing = await self.get_summary(conversation_id)
        if existing:
            existing.content = content
            existing.summarized_up_to_seq = up_to_seq
        else:
            self._session.add(
                ConversationSummaryORM(
                    id=str(uuid4()),
                    conversation_id=conversation_id,
                    content=content,
                    summarized_up_to_seq=up_to_seq,
                )
            )
        await self._session.commit()

    async def count_messages(self, conversation_id: str) -> int:
        stmt = select(func.count()).where(
            MessageORM.conversation_id == conversation_id
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()
