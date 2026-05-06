from __future__ import annotations
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from backend.core.models.chat import RetrievedChunk
from backend.core.models.knowledge import ChunkWithEmbedding
from backend.db.models.knowledge import KnowledgeChunkORM, KnowledgeDocQuestionORM


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
            distance_col = KnowledgeChunkORM.embedding.cosine_distance(query_vector).label("distance")
            stmt = (
                select(KnowledgeChunkORM, distance_col)
                .order_by(distance_col)
                .limit(top_k)
            )
            if knowledge_base_id is not None:
                stmt = stmt.where(KnowledgeChunkORM.knowledge_base_id == knowledge_base_id)
            result = await session.execute(stmt)
            return [
                RetrievedChunk(
                    content=row.KnowledgeChunkORM.content,
                    score=1.0 - row.distance,
                    metadata=row.KnowledgeChunkORM.metadata_ or {},
                    document_id=row.KnowledgeChunkORM.document_id,
                )
                for row in result.all()
            ]

    async def search_questions(
        self,
        query_vector: list[float],
        top_k: int = 10,
        knowledge_base_id: str | None = None,
    ) -> list[RetrievedChunk]:
        async with self._session_factory() as session:
            # Step 1: 向量检索 questions，获取 document_id 列表（去重保序）
            q_distance = KnowledgeDocQuestionORM.embedding.cosine_distance(query_vector).label("q_distance")
            q_stmt = (
                select(KnowledgeDocQuestionORM.document_id)
                .order_by(q_distance)
                .limit(top_k)
            )
            if knowledge_base_id is not None:
                q_stmt = q_stmt.where(KnowledgeDocQuestionORM.knowledge_base_id == knowledge_base_id)
            q_result = await session.execute(q_stmt)
            doc_ids = list(dict.fromkeys(row[0] for row in q_result.all()))

            if not doc_ids:
                return []

            # Step 2: 在匹配文档内按向量相似度召回 chunks
            chunk_distance = KnowledgeChunkORM.embedding.cosine_distance(query_vector).label("distance")
            chunk_stmt = (
                select(KnowledgeChunkORM, chunk_distance)
                .where(KnowledgeChunkORM.document_id.in_(doc_ids))
                .order_by(chunk_distance)
                .limit(top_k)
            )
            chunk_result = await session.execute(chunk_stmt)
            return [
                RetrievedChunk(
                    content=row.KnowledgeChunkORM.content,
                    score=1.0 - row.distance,
                    metadata=row.KnowledgeChunkORM.metadata_ or {},
                    document_id=row.KnowledgeChunkORM.document_id,
                )
                for row in chunk_result.all()
            ]

    async def upsert(
        self, chunks: list[ChunkWithEmbedding], metadata: dict
    ) -> None:
        knowledge_base_id = metadata.get("knowledge_base_id", "")
        document_id = metadata.get("document_id", "")
        async with self._session_factory() as session:
            for item in chunks:
                chunk_meta = dict(item.chunk.metadata)
                session.add(
                    KnowledgeChunkORM(
                        id=str(uuid4()),
                        document_id=document_id,
                        knowledge_base_id=knowledge_base_id,
                        content=item.chunk.content,
                        chunk_index=item.chunk.chunk_index,
                        embedding=item.embedding,
                        metadata_=chunk_meta,
                    )
                )
            await session.commit()
