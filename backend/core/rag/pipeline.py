from __future__ import annotations
import asyncio
import logging
import time
from typing import Any, AsyncIterator
from backend.core.models.chat import ChatEvent, ChatRequest, GuidanceEvent, LLMEvent, SourceItem, SourcesEvent
from backend.core.rag.memory import SlidingWindowMemory
from backend.core.rag.rewrite import LLMQueryRewriter
from backend.core.rag.intent import LLMIntentClassifier
from backend.core.rag.retrieve import MultiChannelRetriever
from backend.core.rag.prompt import PromptBuilder
from backend.core.rag.term_mapper import QueryTermMapper
from backend.core.rag.tracer import RagTracer
from backend.core.rag.protocols import LLMProvider
from backend.infra.rerank.bailian import BailianRerankClient

logger = logging.getLogger("backend.rag.pipeline")


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
        term_mapper: QueryTermMapper | None = None,
        doc_repo: Any = None,
    ) -> None:
        self._llm = llm
        self._memory = memory
        self._rewriter = rewriter
        self._intent_classifier = intent_classifier
        self._retriever = retriever
        self._prompt_builder = prompt_builder
        self._tracer = tracer
        self._reranker = reranker
        self._term_mapper = term_mapper
        self._doc_repo = doc_repo

    async def chat(self, request: ChatRequest) -> AsyncIterator[ChatEvent]:
        start = time.monotonic()
        logger.info(
            "[RAG] ▶ 开始处理 | conv=%s query=%r deep_thinking=%s",
            request.conversation_id, request.query, request.deep_thinking,
        )
        await self._tracer.start_run(
            conversation_id=request.conversation_id, query=request.query
        )
        answer_parts: list[str] = []
        try:
            # ── Step 1: 加载会话历史 ──
            t0 = time.monotonic()
            history = await self._tracer.trace_node("memory_load")(
                self._memory.load
            )(request.conversation_id)
            logger.info(
                "[RAG] ① 会话历史加载 | %.1fms | messages=%d summary=%s",
                (time.monotonic() - t0) * 1000,
                len(history.messages),
                "有" if history.summary else "无",
            )

            # ── Step 2: 术语映射 ──
            expanded_query = request.query
            if self._term_mapper:
                t0 = time.monotonic()
                expanded_query = await self._tracer.trace_node("term_mapping")(
                    self._term_mapper.expand
                )(request.query)
                changed = expanded_query != request.query
                logger.info(
                    "[RAG] ② 术语映射 | %.1fms | changed=%s | query=%r → %r",
                    (time.monotonic() - t0) * 1000,
                    changed, request.query, expanded_query,
                )

            # ── Step 3: 查询改写 ──
            t0 = time.monotonic()
            rewritten = await self._tracer.trace_node("query_rewrite")(
                self._rewriter.rewrite
            )(expanded_query, history)
            logger.info(
                "[RAG] ③ 查询改写 | %.1fms | %r → %r",
                (time.monotonic() - t0) * 1000, expanded_query, rewritten,
            )

            # ── Step 4: 查询拆分 ──
            t0 = time.monotonic()
            sub_queries = await self._tracer.trace_node("query_split")(
                self._rewriter.split
            )(rewritten)
            logger.info(
                "[RAG] ④ 查询拆分 | %.1fms | count=%d | sub_queries=%s",
                (time.monotonic() - t0) * 1000,
                len(sub_queries), sub_queries,
            )

            # ── Step 5: 意图分类 ──
            t0 = time.monotonic()
            intents = await asyncio.gather(
                *[self._intent_classifier.classify(q) for q in sub_queries]
            )
            intent_summary = [
                f"(q={q!r}, guidance={ir.needs_guidance}, type={ir.matched_node.intent_type if ir.matched_node else 'none'}, conf={ir.confidence:.2f})"
                for q, ir in zip(sub_queries, intents)
            ]
            logger.info(
                "[RAG] ⑤ 意图分类 | %.1fms | %s",
                (time.monotonic() - t0) * 1000, " | ".join(intent_summary),
            )

            for intent in intents:
                if intent.needs_guidance:
                    logger.info("[RAG] ✘ 意图不确定，返回引导事件")
                    yield GuidanceEvent(intent=intent)
                    return

            # SYSTEM fast-path: no intent matched → skip retrieval (system fallback)
            if all(ir.matched_node is None for ir in intents):
                logger.info("[RAG] ⑥ 无匹配意图节点，跳过检索，直接生成(system回退)")
                prompt = self._prompt_builder.build(
                    request.query, history, [], list(intents)
                )
                yield SourcesEvent(sources=[])
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
                logger.info("[RAG] ■ 完成(system直答) | total=%dms", total_ms)
                return

            # ── Step 6: 多通道检索 ──
            t0 = time.monotonic()
            retrieved = await self._tracer.trace_node("retrieval")(
                self._retriever.retrieve
            )(sub_queries, intents)
            logger.info(
                "[RAG] ⑥ 多通道检索 | %.1fms | chunks=%d",
                (time.monotonic() - t0) * 1000, len(retrieved),
            )

            # ── Step 7: 重排序 ──
            if self._reranker is not None:
                t0 = time.monotonic()
                pre_count = len(retrieved)
                retrieved = await self._reranker.rerank(request.query, retrieved)
                logger.info(
                    "[RAG] ⑦ 重排序 | %.1fms | %d → %d chunks",
                    (time.monotonic() - t0) * 1000, pre_count, len(retrieved),
                )
            else:
                logger.info("[RAG] ⑦ 重排序 | 跳过(未配置reranker)")

            # ── Step 8: 组装Sources ──
            doc_ids = list({c.document_id for c in retrieved if c.document_id})
            doc_name_map = await self._doc_repo.batch_get_names(doc_ids) if doc_ids else {}
            source_items = [
                SourceItem(
                    ref=i + 1,
                    document_id=c.document_id,
                    document_name=doc_name_map.get(c.document_id),
                    score=c.score,
                    content=c.content,
                )
                for i, c in enumerate(retrieved)
            ]
            logger.info(
                "[RAG] ⑧ 组装来源 | docs=%d sources=%d",
                len(doc_ids), len(source_items),
            )
            yield SourcesEvent(sources=source_items)

            # ── Step 9: 构建Prompt ──
            t0 = time.monotonic()
            prompt = self._prompt_builder.build(
                request.query, history, retrieved, list(intents)
            )
            logger.info(
                "[RAG] ⑨ 构建Prompt | %.1fms | messages=%d",
                (time.monotonic() - t0) * 1000, len(prompt),
            )

            # ── Step 10: LLM流式生成 ──
            t0 = time.monotonic()
            extra_kwargs: dict[str, Any] = {}
            if request.deep_thinking:
                extra_kwargs["extra_body"] = {"enable_thinking": True}
            async for event in self._llm.stream(prompt, **extra_kwargs):
                if event.type == "content":
                    answer_parts.append(event.content)
                yield event
            logger.info(
                "[RAG] ⑩ LLM生成 | %.1fms | answer_len=%d",
                (time.monotonic() - t0) * 1000, len("".join(answer_parts)),
            )

            # ── Step 11: 保存记忆 ──
            await self._memory.save(
                request.conversation_id,
                query=request.query,
                answer="".join(answer_parts),
            )
            total_ms = int((time.monotonic() - start) * 1000)
            await self._tracer.finish_run(status="success", total_duration_ms=total_ms)
            logger.info("[RAG] ■ 完成 | total=%dms", total_ms)

        except Exception:
            total_ms = int((time.monotonic() - start) * 1000)
            await self._tracer.finish_run(status="failed", total_duration_ms=total_ms)
            logger.exception("[RAG] ✘ 处理失败 | total=%dms", total_ms)
            raise
