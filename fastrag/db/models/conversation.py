from __future__ import annotations
from datetime import datetime
from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from fastrag.db.models.base import Base


class ConversationORM(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    messages: Mapped[list[MessageORM]] = relationship(
        back_populates="conversation", order_by="MessageORM.seq"
    )
    summary: Mapped[ConversationSummaryORM | None] = relationship(
        back_populates="conversation"
    )


class MessageORM(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"))
    seq: Mapped[int] = mapped_column()
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    conversation: Mapped[ConversationORM] = relationship(back_populates="messages")


class ConversationSummaryORM(Base):
    __tablename__ = "conversation_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id"), unique=True
    )
    content: Mapped[str] = mapped_column(Text)
    summarized_up_to_seq: Mapped[int] = mapped_column()
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
    conversation: Mapped[ConversationORM] = relationship(back_populates="summary")
