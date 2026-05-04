from __future__ import annotations
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models.knowledge import (
    KnowledgeBaseORM, KnowledgeDocumentORM, KnowledgeChunkORM, KnowledgeDocQuestionORM
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

    async def create_knowledge_base(
        self,
        name: str,
        description: str,
        ingestion_config: dict,
    ) -> KnowledgeBaseORM:
        kb = KnowledgeBaseORM(
            id=str(uuid4()),
            name=name,
            description=description,
            ingestion_config=ingestion_config,
        )
        self._session.add(kb)
        await self._session.commit()
        await self._session.refresh(kb)
        return kb

    async def list_knowledge_bases(self) -> list[KnowledgeBaseORM]:
        result = await self._session.execute(select(KnowledgeBaseORM))
        return list(result.scalars().all())

    async def get_knowledge_base(self, kb_id: str) -> KnowledgeBaseORM | None:
        result = await self._session.execute(
            select(KnowledgeBaseORM).where(KnowledgeBaseORM.id == kb_id)
        )
        return result.scalar_one_or_none()

    async def delete_knowledge_base(self, kb_id: str) -> None:
        from sqlalchemy import delete
        await self._session.execute(
            delete(KnowledgeBaseORM).where(KnowledgeBaseORM.id == kb_id)
        )
        await self._session.commit()

    async def delete_document(self, doc_id: str) -> bool:
        from sqlalchemy import delete
        doc = await self.get_document(doc_id)
        if not doc:
            return False
        await self._session.execute(
            delete(KnowledgeDocQuestionORM).where(KnowledgeDocQuestionORM.document_id == doc_id)
        )
        await self._session.execute(
            delete(KnowledgeChunkORM).where(KnowledgeChunkORM.document_id == doc_id)
        )
        await self._session.execute(
            delete(KnowledgeDocumentORM).where(KnowledgeDocumentORM.id == doc_id)
        )
        await self._session.commit()
        return True

    async def list_documents(self, kb_id: str) -> list[KnowledgeDocumentORM]:
        result = await self._session.execute(
            select(KnowledgeDocumentORM).where(
                KnowledgeDocumentORM.knowledge_base_id == kb_id
            )
        )
        return list(result.scalars().all())

    async def list_chunks_by_document(
        self, doc_id: str, page: int = 1, page_size: int = 20
    ) -> tuple[list[KnowledgeChunkORM], int]:
        count_stmt = (
            select(func.count())
            .select_from(KnowledgeChunkORM)
            .where(KnowledgeChunkORM.document_id == doc_id)
        )
        total = (await self._session.execute(count_stmt)).scalar_one()

        stmt = (
            select(KnowledgeChunkORM)
            .where(KnowledgeChunkORM.document_id == doc_id)
            .order_by(KnowledgeChunkORM.chunk_index)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        chunks = list((await self._session.execute(stmt)).scalars().all())
        return chunks, total
