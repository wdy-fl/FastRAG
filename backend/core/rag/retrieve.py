from __future__ import annotations
import asyncio
import json
import logging
from typing import Protocol
from backend.core.models.chat import RetrievedChunk
from backend.core.models.intent import IntentResult
from backend.core.rag.protocols import LLMProvider, VectorStore

logger = logging.getLogger("backend.rag.retrieve")

_KEYWORD_EXTRACT_PROMPT = (
    "从以下查询中提取3-5个用于关键词检索的短关键词，每个关键词1-4个字。"
    'Return a JSON array of strings, e.g. ["keyword1", "keyword2"]. '
    "Return only the JSON array, no explanation."
)


async def _extract_keywords(llm: LLMProvider, query: str) -> list[str]:
    """Extract search keywords from a query using LLM."""
    parts: list[str] = []
    async for event in llm.stream([
        {"role": "user", "content": f"{_KEYWORD_EXTRACT_PROMPT}\n\nQuery: {query}"}
    ]):
        if event.type == "content":
            parts.append(event.content)
    raw = "".join(parts).strip()
    try:
        keywords = json.loads(raw)
        if isinstance(keywords, list):
            result = [str(k).strip() for k in keywords if k]
            logger.debug("关键词提取 | query=%r | keywords=%s", query, result)
            return result
    except (json.JSONDecodeError, ValueError):
        logger.warning("关键词提取JSON解析失败 | query=%r | raw=%s", query, raw[:200])
    return []


class SearchChannel(Protocol):
    async def search(
        self, query: str, intent: IntentResult, top_k: int,
        query_vector: list[float],
        keywords: list[str] | None = None,
    ) -> list[RetrievedChunk]: ...


class VectorSearchChannel:
    def __init__(self, vector_store: VectorStore, llm: LLMProvider) -> None:
        self._store = vector_store
        self._llm = llm

    async def search(
        self, query: str, intent: IntentResult, top_k: int = 10,
        query_vector: list[float] | None = None,
        keywords: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        if query_vector is None:
            vectors = await self._llm.embed([query])
            query_vector = vectors[0]

        kb_id = None
        if intent.matched_node:
            if intent.matched_node.intent_type == "kb" and intent.matched_node.knowledge_base_id:
                kb_id = intent.matched_node.knowledge_base_id

        results = await self._store.search(
            query_vector=query_vector,
            top_k=top_k,
            knowledge_base_id=kb_id,
        )
        logger.debug("VectorSearch | query=%r | kb=%s | top_k=%d | returned=%d", query, kb_id, top_k, len(results))
        return results


class QuestionSearchChannel:
    def __init__(self, vector_store: VectorStore, llm: LLMProvider) -> None:
        self._store = vector_store
        self._llm = llm

    async def search(
        self, query: str, intent: IntentResult, top_k: int = 10,
        query_vector: list[float] | None = None,
        keywords: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        if query_vector is None:
            vectors = await self._llm.embed([query])
            query_vector = vectors[0]

        kb_id = None
        if intent.matched_node:
            if intent.matched_node.intent_type == "kb" and intent.matched_node.knowledge_base_id:
                kb_id = intent.matched_node.knowledge_base_id

        results = await self._store.search_questions(
            query_vector=query_vector,
            top_k=top_k,
            knowledge_base_id=kb_id,
        )
        logger.debug("QuestionSearch | query=%r | kb=%s | top_k=%d | returned=%d", query, kb_id, top_k, len(results))
        return results


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
        chat_llm: LLMProvider | None = None,
    ) -> None:
        self._channels = channels
        self._llm = llm
        self._chat_llm = chat_llm
        self._rrf = RrfProcessor()

    async def retrieve(
        self, queries: list[str], intents: list[IntentResult]
    ) -> list[RetrievedChunk]:
        logger.info(
            "多通道检索开始 | queries=%s | channels=%d",
            queries, len(self._channels),
        )
        query_vectors: dict[str, list[float]] = {}
        query_keywords: dict[str, list[str]] = {}

        if self._llm is not None:
            # Run embedding and keyword extraction in parallel
            embed_task = asyncio.gather(
                *[self._llm.embed([q]) for q in queries]
            )
            if self._chat_llm is not None:
                kw_task = asyncio.gather(
                    *[_extract_keywords(self._chat_llm, q) for q in queries]
                )
                embeddings, kw_results = await asyncio.gather(embed_task, kw_task)
            else:
                embeddings = await embed_task
                kw_results = [[] for _ in queries]
            query_vectors = {q: v[0] for q, v in zip(queries, embeddings)}
            query_keywords = {q: kw for q, kw in zip(queries, kw_results)}
            logger.debug("Embedding计算完成 | queries=%d", len(queries))
            logger.info(
                "关键词提取完成 | %s",
                " | ".join(f"{q!r}→{kw}" for q, kw in query_keywords.items()),
            )

        tasks = [
            channel.search(
                query, intent, top_k=10,
                query_vector=query_vectors.get(query),
                keywords=query_keywords.get(query),
            )
            for query, intent in zip(queries, intents)
            for channel in self._channels
        ]
        channel_results: list[list[RetrievedChunk]] = await asyncio.gather(*tasks)
        # Log per-channel results
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
