from __future__ import annotations
from uuid import uuid4
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models.conversation import (
    ConversationORM, MessageORM, ConversationSummaryORM
)


class ConversationRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all_messages(self, conversation_id: str) -> list[MessageORM]:
        stmt = (
            select(MessageORM)
            .where(MessageORM.conversation_id == conversation_id)
            .order_by(MessageORM.seq.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

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
        self, conversation_id: str, role: str, content: str,
        sources: list[dict] | None = None,
    ) -> MessageORM:
        count = await self.count_messages(conversation_id)
        msg = MessageORM(
            id=str(uuid4()),
            conversation_id=conversation_id,
            seq=count + 1,
            role=role,
            content=content,
            sources=sources,
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

    async def update_title(self, conversation_id: str, title: str) -> None:
        conv = await self.get_conversation(conversation_id)
        if conv:
            conv.title = title
            await self._session.commit()

    async def create_conversation(self, title: str) -> ConversationORM:
        conv = ConversationORM(id=str(uuid4()), title=title)
        self._session.add(conv)
        await self._session.commit()
        await self._session.refresh(conv)
        return conv

    async def list_conversations(self) -> list[ConversationORM]:
        stmt = select(ConversationORM).order_by(ConversationORM.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_conversation(self, conversation_id: str) -> ConversationORM | None:
        stmt = select(ConversationORM).where(ConversationORM.id == conversation_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_conversation(self, conversation_id: str) -> None:
        from sqlalchemy import delete
        from backend.db.models.trace import RagTraceNodeORM, RagTraceRunORM
        # 先删 trace nodes（引用 trace runs）
        run_ids_stmt = select(RagTraceRunORM.id).where(
            RagTraceRunORM.conversation_id == conversation_id
        )
        run_ids_result = await self._session.execute(run_ids_stmt)
        run_ids = run_ids_result.scalars().all()
        if run_ids:
            await self._session.execute(
                delete(RagTraceNodeORM).where(RagTraceNodeORM.run_id.in_(run_ids))
            )
        # 再删 trace runs
        await self._session.execute(
            delete(RagTraceRunORM).where(RagTraceRunORM.conversation_id == conversation_id)
        )
        # 删 summary 和 messages
        await self._session.execute(
            delete(ConversationSummaryORM).where(
                ConversationSummaryORM.conversation_id == conversation_id
            )
        )
        await self._session.execute(
            delete(MessageORM).where(MessageORM.conversation_id == conversation_id)
        )
        # 最后删 conversation
        await self._session.execute(
            delete(ConversationORM).where(ConversationORM.id == conversation_id)
        )
        await self._session.commit()

    async def get_message(self, message_id: str) -> MessageORM | None:
        stmt = select(MessageORM).where(MessageORM.id == message_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_message_feedback(self, message_id: str, feedback: str | None) -> None:
        stmt = select(MessageORM).where(MessageORM.id == message_id)
        result = await self._session.execute(stmt)
        message = result.scalar_one_or_none()
        if message:
            message.feedback = feedback
            await self._session.commit()
