from __future__ import annotations
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastrag.db.models.knowledge import (
    KnowledgeDocumentORM, KnowledgeChunkORM
)


class KnowledgeRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_document(
        self,
        knowledge_base_id: str,
        filename: str,
        source_type: str,
        source_uri: str,
    ) -> KnowledgeDocumentORM:
        doc = KnowledgeDocumentORM(
            id=str(uuid4()),
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            source_type=source_type,
            source_uri=source_uri,
            status="pending",
        )
        self._session.add(doc)
        await self._session.commit()
        await self._session.refresh(doc)
        return doc

    async def get_document(self, doc_id: str) -> KnowledgeDocumentORM | None:
        stmt = select(KnowledgeDocumentORM).where(KnowledgeDocumentORM.id == doc_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_document_status(
        self,
        doc_id: str,
        status: str,
        chunk_count: int = 0,
        error_message: str | None = None,
    ) -> None:
        doc = await self.get_document(doc_id)
        if doc:
            doc.status = status
            doc.chunk_count = chunk_count
            doc.error_message = error_message
            await self._session.commit()

    async def get_chunks_by_document(
        self, doc_id: str
    ) -> list[KnowledgeChunkORM]:
        stmt = (
            select(KnowledgeChunkORM)
            .where(KnowledgeChunkORM.document_id == doc_id)
            .order_by(KnowledgeChunkORM.chunk_index)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
