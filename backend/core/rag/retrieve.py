from __future__ import annotations
import asyncio
from typing import Protocol
from backend.core.models.chat import RetrievedChunk
from backend.core.models.intent import IntentResult
from backend.core.rag.protocols import LLMProvider, VectorStore


class SearchChannel(Protocol):
    async def search(
        self, query: str, intent: IntentResult, top_k: int
    ) -> list[RetrievedChunk]: ...


class SearchResultPostProcessor(Protocol):
    async def process(
        self, results: list[RetrievedChunk]
    ) -> list[RetrievedChunk]: ...


class VectorSearchChannel:
    def __init__(self, vector_store: VectorStore, llm: LLMProvider) -> None:
        self._store = vector_store
        self._llm = llm

    async def search(
        self, query: str, intent: IntentResult, top_k: int = 10
    ) -> list[RetrievedChunk]:
        knowledge_base_id = (
            intent.matched_node.id if intent.matched_node else None
        )
        vectors = await self._llm.embed([query])
        return await self._store.search(
            query_vector=vectors[0],
            top_k=top_k,
            knowledge_base_id=knowledge_base_id,
        )


class DeduplicationProcessor:
    async def process(
        self, results: list[RetrievedChunk]
    ) -> list[RetrievedChunk]:
        seen: dict[str, RetrievedChunk] = {}
        for chunk in results:
            if chunk.content not in seen or chunk.score > seen[chunk.content].score:
                seen[chunk.content] = chunk
        return list(seen.values())


class MultiChannelRetriever:
    def __init__(
        self,
        channels: list[SearchChannel],
        post_processors: list[SearchResultPostProcessor],
    ) -> None:
        self._channels = channels
        self._post_processors = post_processors

    async def retrieve(
        self, queries: list[str], intents: list[IntentResult]
    ) -> list[RetrievedChunk]:
        tasks = [
            channel.search(query, intent, top_k=10)
            for query, intent in zip(queries, intents)
            for channel in self._channels
        ]
        all_results: list[list[RetrievedChunk]] = await asyncio.gather(*tasks)
        merged: list[RetrievedChunk] = [
            chunk for sublist in all_results for chunk in sublist
        ]
        for processor in self._post_processors:
            merged = await processor.process(merged)
        return merged
