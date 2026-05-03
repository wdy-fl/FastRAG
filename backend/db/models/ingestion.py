from __future__ import annotations
from datetime import datetime
from sqlalchemy import ForeignKey, JSON, String, Text, Integer, func
from sqlalchemy.orm import Mapped, mapped_column
from backend.db.models.base import Base


class IngestionTaskORM(Base):
    __tablename__ = "ingestion_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    knowledge_base_id: Mapped[str] = mapped_column(ForeignKey("knowledge_bases.id"))
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id"))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    node_results: Mapped[list] = mapped_column(JSON, default=list)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    def __init__(self, **kw: object) -> None:
        kw.setdefault("status", "pending")
        kw.setdefault("node_results", [])
        super().__init__(**kw)
