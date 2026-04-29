from __future__ import annotations
from datetime import datetime
from sqlalchemy import ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from fastrag.db.models.base import Base


class RagTraceRunORM(Base):
    __tablename__ = "rag_trace_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id"))
    query: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20))
    total_duration_ms: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    nodes: Mapped[list[RagTraceNodeORM]] = relationship(back_populates="run")


class RagTraceNodeORM(Base):
    __tablename__ = "rag_trace_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("rag_trace_runs.id"))
    node_name: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20))
    duration_ms: Mapped[int] = mapped_column(default=0)
    detail: Mapped[dict | None] = mapped_column(JSON)
    run: Mapped[RagTraceRunORM] = relationship(back_populates="nodes")
