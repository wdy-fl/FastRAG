from __future__ import annotations
import asyncio
import time
from typing import Any, AsyncIterator
from backend.core.models.chat import ChatEvent, ChatRequest, GuidanceEvent, LLMEvent
from backend.core.rag.memory import SlidingWindowMemory
from backend.core.rag.rewrite import LLMQueryRewriter
from backend.core.rag.intent import LLMIntentClassifier
from backend.core.rag.retrieve import MultiChannelRetriever
from backend.core.rag.prompt import PromptBuilder
from backend.core.rag.tracer import RagTracer
from backend.core.rag.protocols import LLMProvider
from backend.infra.rerank.bailian import BailianRerankClient


class RAGPipeline:
    def __init__(
        self,
        llm: LLMProvider,
        memory: SlidingWindowMemory,
        rewriter: LLMQueryRewriter,
        intent_classifier: LLMIntentClassifier,
        retriever: MultiChannelRetriever,
        prompt_builder: PromptBuilder,
        tracer: RagTracer,
        reranker: BailianRerankClient | None = None,
    ) -> None:
        self._llm = llm
        self._memory = memory
        self._rewriter = rewriter
        self._intent_classifier = intent_classifier
        self._retriever = retriever
        self._prompt_builder = prompt_builder
        self._tracer = tracer
        self._reranker = reranker

    async def chat(self, request: ChatRequest) -> AsyncIterator[ChatEvent]:
        start = time.monotonic()
        await self._tracer.start_run(
            conversation_id=request.conversation_id, query=request.query
        )
        answer_parts: list[str] = []
        try:
            history = await self._tracer.trace_node("memory_load")(
                self._memory.load
            )(request.conversation_id)

            rewritten = await self._tracer.trace_node("query_rewrite")(
                self._rewriter.rewrite
            )(request.query, history)

            sub_queries = await self._tracer.trace_node("query_split")(
                self._rewriter.split
            )(rewritten)

            intents = await asyncio.gather(
                *[self._intent_classifier.classify(q) for q in sub_queries]
            )

            for intent in intents:
                if intent.needs_guidance:
                    yield GuidanceEvent(intent=intent)
                    return

            retrieved = await self._tracer.trace_node("retrieval")(
                self._retriever.retrieve
            )(sub_queries, intents)

            if self._reranker is not None:
                retrieved = await self._reranker.rerank(request.query, retrieved)

            prompt = self._prompt_builder.build(
                request.query, history, retrieved, list(intents)
            )

            extra_kwargs: dict[str, Any] = {}
            if request.deep_thinking:
                extra_kwargs["extra_body"] = {"enable_thinking": True}
            async for event in self._llm.stream(prompt, **extra_kwargs):
                if event.type == "content":
                    answer_parts.append(event.content)
                yield event

            await self._memory.save(
                request.conversation_id,
                query=request.query,
                answer="".join(answer_parts),
            )
            total_ms = int((time.monotonic() - start) * 1000)
            await self._tracer.finish_run(status="success", total_duration_ms=total_ms)

        except Exception:
            total_ms = int((time.monotonic() - start) * 1000)
            await self._tracer.finish_run(status="failed", total_duration_ms=total_ms)
            raise
