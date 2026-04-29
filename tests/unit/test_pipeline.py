import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastrag.core.rag.pipeline import RAGPipeline
from fastrag.core.models.chat import (
    ChatRequest, ConversationHistory, LLMEvent, GuidanceEvent,
)
from fastrag.core.models.intent import IntentResult


def _make_pipeline(needs_guidance=False, llm_content="Hello!"):
    mock_llm = AsyncMock()

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
    mock_rewriter.split = AsyncMock(return_value=["rewritten query"])

    mock_intent = AsyncMock()
    mock_intent.classify = AsyncMock(
        return_value=IntentResult(needs_guidance=needs_guidance)
    )

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
