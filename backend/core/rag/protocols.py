from __future__ import annotations
from typing import AsyncIterator, Protocol, runtime_checkable
from backend.core.models.chat import (
    LLMEvent, ConversationHistory, RetrievedChunk,
)
from backend.core.models.knowledge import ChunkWithEmbedding
from backend.core.models.intent import IntentResult


@runtime_checkable
class LLMProvider(Protocol):
    async def stream(
        self, messages: list[dict], **kwargs
    ) -> AsyncIterator[LLMEvent]: ...

    async def chat(
        self, messages: list[dict], **kwargs
    ) -> str: ...

    async def embed(
        self, texts: list[str], model: str | None = None
    ) -> list[list[float]]: ...

    async def close(self) -> None: ...


@runtime_checkable
class VectorStore(Protocol):
    async def search(
        self,
        query_vector: list[float],
        top_k: int,
        knowledge_base_id: str | None = None,
    ) -> list[RetrievedChunk]: ...

    async def search_questions(
        self,
        query_vector: list[float],
        top_k: int,
        knowledge_base_id: str | None,
    ) -> list[RetrievedChunk]: ...

    async def upsert(
        self, chunks: list[ChunkWithEmbedding], metadata: dict
    ) -> None: ...


@runtime_checkable
class ConversationMemory(Protocol):
    async def load(self, conversation_id: str) -> ConversationHistory: ...
    async def save(
        self, conversation_id: str, query: str, answer: str
    ) -> None: ...


@runtime_checkable
class QueryRewriter(Protocol):
    async def rewrite(
        self, query: str, history: ConversationHistory
    ) -> str: ...


@runtime_checkable
class IntentClassifier(Protocol):
    async def classify(self, query: str) -> IntentResult: ...


@runtime_checkable
class Reranker(Protocol):
    async def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_n: int | None = None,
    ) -> list[RetrievedChunk]: ...
