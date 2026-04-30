from __future__ import annotations
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from backend.core.models.chat import RetrievedChunk
from backend.core.models.knowledge import ChunkWithEmbedding
from backend.db.models.knowledge import KnowledgeChunkORM


class PgVectorStore:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        knowledge_base_id: str | None = None,
    ) -> list[RetrievedChunk]:
        async with self._session_factory() as session:
            stmt = (
                select(KnowledgeChunkORM)
                .order_by(KnowledgeChunkORM.embedding.cosine_distance(query_vector))
                .limit(top_k)
            )
            if knowledge_base_id is not None:
                stmt = stmt.where(
                    KnowledgeChunkORM.knowledge_base_id == knowledge_base_id
                )
            result = await session.execute(stmt)
            rows = result.scalars().all()
            return [
                RetrievedChunk(
                    content=row.content,
                    score=1.0,  # cosine_distance doesn't return score directly; caller can rerank
                    metadata=row.metadata_ or {},
                    document_id=row.document_id,
                )
                for row in rows
            ]

    async def upsert(
        self, chunks: list[ChunkWithEmbedding], metadata: dict
    ) -> None:
        knowledge_base_id = metadata.get("knowledge_base_id", "")
        document_id = metadata.get("document_id", "")
        async with self._session_factory() as session:
            for item in chunks:
                session.add(
                    KnowledgeChunkORM(
                        id=str(uuid4()),
                        document_id=document_id,
                        knowledge_base_id=knowledge_base_id,
                        content=item.chunk.content,
                        chunk_index=item.chunk.chunk_index,
                        embedding=item.embedding,
                        metadata_=item.chunk.metadata,
                    )
                )
            await session.commit()
