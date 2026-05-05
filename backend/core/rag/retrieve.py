from __future__ import annotations
import asyncio
from typing import Protocol
from backend.core.models.chat import RetrievedChunk
from backend.core.models.intent import IntentResult
from backend.core.rag.protocols import LLMProvider, VectorStore


class SearchChannel(Protocol):
    async def search(
        self, query: str, intent: IntentResult, top_k: int,
        query_vector: list[float],
    ) -> list[RetrievedChunk]: ...


class VectorSearchChannel:
    def __init__(self, vector_store: VectorStore, llm: LLMProvider) -> None:
        self._store = vector_store
        self._llm = llm

    async def search(
        self, query: str, intent: IntentResult, top_k: int = 10,
        query_vector: list[float] | None = None,
    ) -> list[RetrievedChunk]:
        if query_vector is None:
            vectors = await self._llm.embed([query])
            query_vector = vectors[0]

        kb_id = None
        if intent.matched_node:
            if intent.matched_node.intent_type == "kb" and intent.matched_node.knowledge_base_id:
                kb_id = intent.matched_node.knowledge_base_id

        return await self._store.search(
            query_vector=query_vector,
            top_k=top_k,
            knowledge_base_id=kb_id,
        )


class QuestionSearchChannel:
    def __init__(self, vector_store: VectorStore, llm: LLMProvider) -> None:
        self._store = vector_store
        self._llm = llm

    async def search(
        self, query: str, intent: IntentResult, top_k: int = 10,
        query_vector: list[float] | None = None,
    ) -> list[RetrievedChunk]:
        if query_vector is None:
            vectors = await self._llm.embed([query])
            query_vector = vectors[0]

        kb_id = None
        if intent.matched_node:
            if intent.matched_node.intent_type == "kb" and intent.matched_node.knowledge_base_id:
                kb_id = intent.matched_node.knowledge_base_id

        return await self._store.search_questions(
            query_vector=query_vector,
            top_k=top_k,
            knowledge_base_id=kb_id,
        )


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
        llm: LLMProvider | None = None,
    ) -> None:
        self._channels = channels
        self._llm = llm
        self._rrf = RrfProcessor()

    async def retrieve(
        self, queries: list[str], intents: list[IntentResult]
    ) -> list[RetrievedChunk]:
        query_vectors: dict[str, list[float]] = {}
        if self._llm is not None:
            embeddings = await asyncio.gather(
                *[self._llm.embed([q]) for q in queries]
            )
            query_vectors = {q: v[0] for q, v in zip(queries, embeddings)}

        tasks = [
            channel.search(
                query, intent, top_k=10,
                query_vector=query_vectors.get(query),
            )
            for query, intent in zip(queries, intents)
            for channel in self._channels
        ]
        channel_results: list[list[RetrievedChunk]] = await asyncio.gather(*tasks)
        return await self._rrf.process(channel_results)
