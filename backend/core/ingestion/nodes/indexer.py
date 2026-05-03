from __future__ import annotations
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from backend.core.models.ingestion import IndexerSettings, IngestionContext
from backend.core.models.knowledge import ChunkWithEmbedding, DocumentChunk
from backend.core.rag.protocols import LLMProvider, VectorStore
from backend.core.exceptions import IngestionError
from backend.db.models.knowledge import KnowledgeDocQuestionORM


class IndexerNode:
    name = "indexer"

    def __init__(
        self,
        llm: LLMProvider,
        vector_store: VectorStore,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._llm = llm
        self._vector_store = vector_store
        self._session_factory = session_factory

    async def execute(
        self, context: IngestionContext, config: IndexerSettings
    ) -> IngestionContext:
        if not context.chunks:
            raise IngestionError("IndexerNode requires chunks to be set by ChunkerNode")

        embedded: list[ChunkWithEmbedding] = []
        for i in range(0, len(context.chunks), config.batch_size):
            batch = context.chunks[i : i + config.batch_size]
            texts = [c.content for c in batch]
            vectors = await self._llm.embed(texts)
            for chunk, vector in zip(batch, vectors):
                keywords: list[str] = chunk.metadata.get("keywords", [])
                enriched_metadata = {**chunk.metadata, "_keywords_str": " ".join(keywords)}
                chunk_copy = DocumentChunk(
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    metadata=enriched_metadata,
                )
                embedded.append(ChunkWithEmbedding(chunk=chunk_copy, embedding=vector))

        await self._vector_store.upsert(embedded, metadata=context.metadata)
        context.embedded_chunks = embedded

        if context.questions and self._session_factory:
            await self._persist_questions(context)

        return context

    async def _persist_questions(self, context: IngestionContext) -> None:
        document_id = context.metadata.get("document_id", "")
        knowledge_base_id = context.metadata.get("knowledge_base_id", "")
        if not document_id or not knowledge_base_id:
            return
        embeddings = await self._llm.embed(context.questions)
        try:
            async with self._session_factory() as session:
                for question, embedding in zip(context.questions, embeddings):
                    session.add(KnowledgeDocQuestionORM(
                        id=str(uuid4()),
                        document_id=document_id,
                        knowledge_base_id=knowledge_base_id,
                        question=question,
                        embedding=embedding,
                    ))
                await session.commit()
        except Exception as exc:
            raise IngestionError(f"Failed to persist questions: {exc}") from exc
