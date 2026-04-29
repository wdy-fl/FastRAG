import pytest
from unittest.mock import AsyncMock
from fastrag.core.rag.rewrite import LLMQueryRewriter
from fastrag.core.rag.intent import LLMIntentClassifier
from fastrag.core.models.chat import ConversationHistory, LLMEvent
from fastrag.core.models.intent import IntentResult


async def _make_llm_stream(content: str):
    async def _gen():
        yield LLMEvent(type="content", content=content)
    return _gen()


def _sync_make_llm_stream(content: str):
    async def _gen():
        yield LLMEvent(type="content", content=content)
    return _gen()


@pytest.mark.asyncio
async def test_rewriter_rewrite_returns_string():
    mock_llm = AsyncMock()
    mock_llm.stream = AsyncMock(side_effect=lambda msgs, **kw: _sync_make_llm_stream("Rewritten query"))

    rewriter = LLMQueryRewriter(llm=mock_llm)
    result = await rewriter.rewrite("what is ml?", ConversationHistory())
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_rewriter_split_returns_list():
    mock_llm = AsyncMock()
    mock_llm.stream = AsyncMock(
        side_effect=lambda msgs, **kw: _sync_make_llm_stream("1. What is ML?\n2. How does it work?")
    )
    rewriter = LLMQueryRewriter(llm=mock_llm)
    parts = await rewriter.split("What is ML and how does it work?")
    assert isinstance(parts, list)
    assert len(parts) >= 1


@pytest.mark.asyncio
async def test_classifier_returns_intent_result():
    mock_llm = AsyncMock()
    mock_llm.stream = AsyncMock(
        side_effect=lambda msgs, **kw: _sync_make_llm_stream('{"confidence": 0.9, "matched_id": null}')
    )
    classifier = LLMIntentClassifier(llm=mock_llm, intent_nodes=[], confidence_threshold=0.6)
    result = await classifier.classify("What is machine learning?")
    assert isinstance(result, IntentResult)


@pytest.mark.asyncio
async def test_classifier_low_confidence_needs_guidance():
    mock_llm = AsyncMock()
    mock_llm.stream = AsyncMock(
        side_effect=lambda msgs, **kw: _sync_make_llm_stream('{"confidence": 0.3, "matched_id": null}')
    )
    classifier = LLMIntentClassifier(llm=mock_llm, intent_nodes=[], confidence_threshold=0.6)
    result = await classifier.classify("ambiguous question")
    assert result.needs_guidance is True
