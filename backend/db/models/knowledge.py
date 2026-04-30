from __future__ import annotations
from datetime import datetime
from sqlalchemy import ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from backend.db.models.base import Base
from backend.config.settings import Settings


_settings = Settings()
_EMBEDDING_DIM = _settings.embedding.dimensions


class KnowledgeBaseORM(Base):
    __tablename__ = "knowledge_bases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    ingestion_config: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    documents: Mapped[list[KnowledgeDocumentORM]] = relationship(
        back_populates="knowledge_base"
    )


class KnowledgeDocumentORM(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    knowledge_base_id: Mapped[str] = mapped_column(ForeignKey("knowledge_bases.id"))
    filename: Mapped[str] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(20))
    source_uri: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    chunk_count: Mapped[int] = mapped_column(default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    knowledge_base: Mapped[KnowledgeBaseORM] = relationship(
        back_populates="documents"
    )


class KnowledgeChunkORM(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("knowledge_documents.id"))
    knowledge_base_id: Mapped[str] = mapped_column(ForeignKey("knowledge_bases.id"))
    content: Mapped[str] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column()
    embedding: Mapped[list[float]] = mapped_column(Vector(_EMBEDDING_DIM))
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, default={})
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class QueryTermMappingORM(Base):
    __tablename__ = "query_term_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_term: Mapped[str] = mapped_column(String(200))
    target_term: Mapped[str] = mapped_column(String(200))
    knowledge_base_id: Mapped[str | None] = mapped_column(
        ForeignKey("knowledge_bases.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
