import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from backend.core.rag.pipeline import RAGPipeline
from backend.core.models.chat import (
    ChatRequest, ConversationHistory, LLMEvent, GuidanceEvent, RetrievedChunk,
)
from backend.core.models.intent import IntentMatch, IntentNode, IntentResult


def _make_stream(content: str):
    async def _gen():
        yield LLMEvent(type="content", content=content)
        yield LLMEvent(type="done", content="")
    return _gen()


def _make_pipeline(
    needs_guidance=False,
    llm_content="Hello!",
    llm_stream_fn=None,
    llm=None,
    retriever=None,
    reranker=None,
    intent_classifier=None,
):
    if llm is not None:
        mock_llm = llm
    else:
        mock_llm = AsyncMock()
        if llm_stream_fn is not None:
            mock_llm.stream = llm_stream_fn
        else:
            def fake_stream(messages, **kwargs):
                async def _gen():
                    yield LLMEvent(type="content", content=llm_content)
                    yield LLMEvent(type="done", content="")
                return _gen()
            mock_llm.stream = fake_stream

    mock_memory = AsyncMock()
    mock_memory.load = AsyncMock(return_value=ConversationHistory())
    mock_memory.save = AsyncMock()

    mock_rewriter = AsyncMock()
    mock_rewriter.rewrite = AsyncMock(return_value="rewritten query")

    if intent_classifier is not None:
        mock_intent = intent_classifier
    else:
        mock_intent = AsyncMock()
        mock_intent.classify = AsyncMock(
            return_value=IntentResult(needs_guidance=needs_guidance)
        )

    if retriever is not None:
        mock_retriever = retriever
    else:
        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=[])

    mock_prompt = MagicMock()
    mock_prompt.build = MagicMock(
        return_value=[{"role": "user", "content": "test"}]
    )

    mock_tracer = AsyncMock()
    mock_tracer.start_run = AsyncMock(return_value="run-1")
    mock_tracer.finish_run = AsyncMock()

    def trace_node(name):
        def decorator(fn):
            return fn
        return decorator

    mock_tracer.trace_node = trace_node

    return RAGPipeline(
        llm=mock_llm,
        memory=mock_memory,
        rewriter=mock_rewriter,
        intent_classifier=mock_intent,
        retriever=mock_retriever,
        prompt_builder=mock_prompt,
        tracer=mock_tracer,
        reranker=reranker,
    )


@pytest.mark.asyncio
async def test_pipeline_chat_yields_llm_events():
    pipeline = _make_pipeline(llm_content="Hello!")
    request = ChatRequest(query="What is AI?", conversation_id="conv-1")

    events = []
    async for event in pipeline.chat(request):
        events.append(event)

    assert any(isinstance(e, LLMEvent) and e.type == "content" for e in events)


@pytest.mark.asyncio
async def test_pipeline_chat_returns_guidance_on_low_confidence():
    pipeline = _make_pipeline(needs_guidance=True)
    request = ChatRequest(query="ambiguous", conversation_id="conv-1")

    events = []
    async for event in pipeline.chat(request):
        events.append(event)

    assert len(events) == 1
    assert isinstance(events[0], GuidanceEvent)


@pytest.mark.asyncio
async def test_pipeline_saves_memory_after_chat():
    pipeline = _make_pipeline(llm_content="Answer here.")
    request = ChatRequest(query="test", conversation_id="conv-1")

    events = [event async for event in pipeline.chat(request)]
    pipeline._memory.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_passes_deep_thinking_to_llm():
    """deep_thinking=True 时，extra_body={"enable_thinking": True} 必须被传入 LLM stream。"""
    captured_kwargs: dict = {}

    async def capturing_stream(messages, **kwargs):
        captured_kwargs.update(kwargs)
        yield LLMEvent(type="content", content="hello")
        yield LLMEvent(type="done", content="")

    pipeline = _make_pipeline(llm_stream_fn=capturing_stream)
    req = ChatRequest(query="test", conversation_id="c1", deep_thinking=True)
    events = [e async for e in pipeline.chat(req)]
    assert any(e.type in ("content", "done") for e in events)
    assert captured_kwargs.get("extra_body") == {"enable_thinking": True}


@pytest.mark.asyncio
async def test_pipeline_calls_reranker_when_provided():
    """当 reranker 存在时，pipeline 应在 retrieval 之后调用 reranker.rerank()。"""
    mock_llm = MagicMock()
    mock_llm.stream = MagicMock(side_effect=lambda msgs, **kw: _make_stream("answer"))

    mock_retriever = AsyncMock()
    mock_retriever.retrieve = AsyncMock(
        return_value=[RetrievedChunk(content="chunk", score=0.9)]
    )

    mock_reranker = AsyncMock()
    mock_reranker.rerank = AsyncMock(
        return_value=[RetrievedChunk(content="reranked chunk", score=0.95)]
    )

    mock_intent = AsyncMock()
    mock_intent.classify = AsyncMock(
        return_value=IntentResult(
            matches=[IntentMatch(node=IntentNode(id="n1", name="test"), confidence="high")]
        )
    )

    pipeline = _make_pipeline(
        llm=mock_llm,
        retriever=mock_retriever,
        reranker=mock_reranker,
        intent_classifier=mock_intent,
    )
    events = []
    async for event in pipeline.chat(ChatRequest(query="test", conversation_id="c1")):
        events.append(event)

    mock_reranker.rerank.assert_awaited_once()
    call_args = mock_reranker.rerank.call_args
    assert call_args[0][0] == "test"  # query 参数


@pytest.mark.asyncio
async def test_pipeline_skips_reranker_when_none():
    mock_llm = MagicMock()
    mock_llm.stream = MagicMock(side_effect=lambda msgs, **kw: _make_stream("answer"))

    mock_retriever = AsyncMock()
    mock_retriever.retrieve = AsyncMock(
        return_value=[RetrievedChunk(content="chunk", score=0.9)]
    )

    pipeline = _make_pipeline(llm=mock_llm, retriever=mock_retriever, reranker=None)
    events = []
    async for event in pipeline.chat(ChatRequest(query="test", conversation_id="c1")):
        events.append(event)

    # 验证 pipeline 正常完成，不抛异常
    assert any(e.type == "done" for e in events if hasattr(e, "type"))


@pytest.mark.asyncio
async def test_pipeline_fast_path_on_no_intent_match():
    """No matched node → skip retrieval, direct LLM answer (system fallback)."""
    mock_intent = AsyncMock()
    mock_intent.classify = AsyncMock(
        return_value=IntentResult()
    )

    mock_retriever = AsyncMock()
    mock_retriever.retrieve = AsyncMock(return_value=[])

    pipeline = _make_pipeline(intent_classifier=mock_intent, retriever=mock_retriever)
    request = ChatRequest(query="你好", conversation_id="conv-1")

    events = [e async for e in pipeline.chat(request)]

    # Should have LLM content events
    assert any(isinstance(e, LLMEvent) and e.type == "content" for e in events)
    # Should NOT call retrieval
    mock_retriever.retrieve.assert_not_awaited()
