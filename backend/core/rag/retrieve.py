from __future__ import annotations
import asyncio
from typing import Protocol
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from backend.core.models.chat import RetrievedChunk
from backend.core.models.intent import IntentResult
from backend.core.rag.protocols import LLMProvider, VectorStore
from backend.db.models.knowledge import KnowledgeChunkORM


class SearchChannel(Protocol):
    async def search(
        self, query: str, intent: IntentResult, top_k: int
    ) -> list[RetrievedChunk]: ...


class VectorSearchChannel:
    def __init__(self, vector_store: VectorStore, llm: LLMProvider) -> None:
        self._store = vector_store
        self._llm = llm

    async def search(
        self, query: str, intent: IntentResult, top_k: int = 10
    ) -> list[RetrievedChunk]:
        knowledge_base_id = intent.matched_node.id if intent.matched_node else None
        vectors = await self._llm.embed([query])
        return await self._store.search(
            query_vector=vectors[0],
            top_k=top_k,
            knowledge_base_id=knowledge_base_id,
        )


class QuestionSearchChannel:
    def __init__(self, vector_store: VectorStore, llm: LLMProvider) -> None:
        self._store = vector_store
        self._llm = llm

    async def search(
        self, query: str, intent: IntentResult, top_k: int = 10
    ) -> list[RetrievedChunk]:
        knowledge_base_id = intent.matched_node.id if intent.matched_node else None
        vectors = await self._llm.embed([query])
        return await self._store.search_questions(
            query_vector=vectors[0],
            top_k=top_k,
            knowledge_base_id=knowledge_base_id,
        )


class KeywordSearchChannel:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def search(
        self, query: str, intent: IntentResult, top_k: int = 10
    ) -> list[RetrievedChunk]:
        knowledge_base_id = intent.matched_node.id if intent.matched_node else None
        async with self._session_factory() as session:
            tsquery = func.plainto_tsquery('simple', query)
            rank_col = func.ts_rank(KnowledgeChunkORM.keywords_tsv, tsquery).label("rank")
            stmt = (
                select(KnowledgeChunkORM, rank_col)
                .where(KnowledgeChunkORM.keywords_tsv.op("@@")(tsquery))
                .order_by(rank_col.desc())
                .limit(top_k)
            )
            if knowledge_base_id is not None:
                stmt = stmt.where(KnowledgeChunkORM.knowledge_base_id == knowledge_base_id)
            result = await session.execute(stmt)
            return [
                RetrievedChunk(
                    content=row.KnowledgeChunkORM.content,
                    score=float(row.rank),
                    metadata=row.KnowledgeChunkORM.metadata_ or {},
                    document_id=row.KnowledgeChunkORM.document_id,
                )
                for row in result.all()
            ]


class RrfProcessor:
    K: int = 60

    async def process(
        self, channel_results: list[list[RetrievedChunk]]
    ) -> list[RetrievedChunk]:
        scores: dict[str, float] = {}
        best_chunk: dict[str, RetrievedChunk] = {}
        for results in channel_results:
            for rank, chunk in enumerate(results):
                key = chunk.content
                scores[key] = scores.get(key, 0.0) + 1.0 / (self.K + rank + 1)
                if key not in best_chunk or chunk.score > best_chunk[key].score:
                    best_chunk[key] = chunk
        sorted_keys = sorted(scores, key=lambda k: scores[k], reverse=True)
        return [best_chunk[k] for k in sorted_keys]


class MultiChannelRetriever:
    def __init__(
        self,
        channels: list[SearchChannel],
    ) -> None:
        self._channels = channels
        self._rrf = RrfProcessor()

    async def retrieve(
        self, queries: list[str], intents: list[IntentResult]
    ) -> list[RetrievedChunk]:
        tasks = [
            channel.search(query, intent, top_k=10)
            for query, intent in zip(queries, intents)
            for channel in self._channels
        ]
        channel_results: list[list[RetrievedChunk]] = await asyncio.gather(*tasks)
        return await self._rrf.process(channel_results)
