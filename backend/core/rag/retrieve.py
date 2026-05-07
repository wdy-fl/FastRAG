from __future__ import annotations
import asyncio
import logging
from typing import Protocol
from backend.core.models.chat import RetrievedChunk
from backend.core.models.intent import IntentResult
from backend.core.rag.protocols import LLMProvider, VectorStore

logger = logging.getLogger("backend.rag.retrieve")


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

        kb_ids = [
            m.node.knowledge_base_id
            for m in intent.matches
            if m.node.intent_type == "kb" and m.node.knowledge_base_id
        ] or [None]

        all_results: list[RetrievedChunk] = []
        for kb_id in kb_ids:
            results = await self._store.search(
                query_vector=query_vector,
                top_k=top_k,
                knowledge_base_id=kb_id,
            )
            all_results.extend(results)
            logger.debug("VectorSearch | query=%r | kb=%s | top_k=%d | returned=%d", query, kb_id, top_k, len(results))
        return all_results


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

        kb_ids = [
            m.node.knowledge_base_id
            for m in intent.matches
            if m.node.intent_type == "kb" and m.node.knowledge_base_id
        ] or [None]

        all_results: list[RetrievedChunk] = []
        for kb_id in kb_ids:
            results = await self._store.search_questions(
                query_vector=query_vector,
                top_k=top_k,
                knowledge_base_id=kb_id,
            )
            all_results.extend(results)
            logger.debug("QuestionSearch | query=%r | kb=%s | top_k=%d | returned=%d", query, kb_id, top_k, len(results))
        return all_results


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
        fused = [best_chunk[k] for k in sorted_keys]
        logger.info(
            "RRF融合 | input_channels=%d | unique_chunks_before=%d | fused=%d",
            len(channel_results),
            sum(len(r) for r in channel_results),
            len(fused),
        )
        return fused


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
        logger.info(
            "多通道检索开始 | queries=%s | channels=%d",
            queries, len(self._channels),
        )
        query_vectors: dict[str, list[float]] = {}

        if self._llm is not None:
            embeddings = await asyncio.gather(
                *[self._llm.embed([q]) for q in queries]
            )
            query_vectors = {q: v[0] for q, v in zip(queries, embeddings)}
            logger.debug("Embedding计算完成 | queries=%d", len(queries))

        tasks = [
            channel.search(
                query, intent, top_k=10,
                query_vector=query_vectors.get(query),
            )
            for query, intent in zip(queries, intents)
            for channel in self._channels
        ]
        channel_results: list[list[RetrievedChunk]] = await asyncio.gather(*tasks)
        channel_names = [
            type(ch).__name__ for ch in self._channels
        ]
        idx = 0
        for qi, (query, intent) in enumerate(zip(queries, intents)):
            for ci, ch_name in enumerate(channel_names):
                count = len(channel_results[idx])
                logger.debug(
                    "  子查询[%d] 通道[%s] | query=%r | results=%d",
                    qi, ch_name, query, count,
                )
                idx += 1
        return await self._rrf.process(channel_results)
