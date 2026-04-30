from __future__ import annotations
from backend.core.models.ingestion import IndexerSettings, IngestionContext
from backend.core.models.knowledge import ChunkWithEmbedding
from backend.core.rag.protocols import LLMProvider, VectorStore
from backend.core.exceptions import IngestionError


class IndexerNode:
    name = "indexer"

    def __init__(self, llm: LLMProvider, vector_store: VectorStore) -> None:
        self._llm = llm
        self._vector_store = vector_store

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
                embedded.append(ChunkWithEmbedding(chunk=chunk, embedding=vector))
        await self._vector_store.upsert(embedded, metadata=context.metadata)
        context.embedded_chunks = embedded
        return context
