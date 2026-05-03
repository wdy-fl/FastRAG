import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.core.rag.rewrite import LLMQueryRewriter
from backend.core.rag.intent import LLMIntentClassifier
from backend.core.rag.retrieve import MultiChannelRetriever, VectorSearchChannel, DeduplicationProcessor
from backend.core.rag.prompt import PromptBuilder
from backend.core.models.chat import ConversationHistory, LLMEvent, RetrievedChunk
from backend.core.models.intent import IntentNode, IntentResult


def _make_stream(content: str):
    """返回 async generator，用于 mock llm.stream()。"""
    async def _gen():
        yield LLMEvent(type="content", content=content)
    return _gen()


@pytest.mark.asyncio
async def test_rewriter_rewrite_returns_string():
    mock_llm = MagicMock()
    mock_llm.stream = MagicMock(side_effect=lambda msgs, **kw: _make_stream("Rewritten query"))

    rewriter = LLMQueryRewriter(llm=mock_llm)
    result = await rewriter.rewrite("what is ml?", ConversationHistory())
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_rewriter_split_returns_list():
    mock_llm = MagicMock()
    mock_llm.stream = MagicMock(
        side_effect=lambda msgs, **kw: _make_stream("1. What is ML?\n2. How does it work?")
    )
    rewriter = LLMQueryRewriter(llm=mock_llm)
    parts = await rewriter.split("What is ML and how does it work?")
    assert isinstance(parts, list)
    assert len(parts) >= 1


@pytest.mark.asyncio
async def test_classifier_returns_intent_result():
    mock_llm = MagicMock()
    mock_llm.stream = MagicMock(
        side_effect=lambda msgs, **kw: _make_stream('{"confidence": 0.9, "matched_id": null}')
    )
    classifier = LLMIntentClassifier(llm=mock_llm, intent_nodes=[], confidence_threshold=0.6)
    result = await classifier.classify("What is machine learning?")
    assert isinstance(result, IntentResult)


@pytest.mark.asyncio
async def test_classifier_low_confidence_needs_guidance():
    mock_llm = MagicMock()
    mock_llm.stream = MagicMock(
        side_effect=lambda msgs, **kw: _make_stream('{"confidence": 0.3, "matched_id": null}')
    )
    # 需要提供至少一个节点，否则 classifier 直接跳过不走 LLM
    dummy_node = IntentNode(id="n1", name="General", level="domain")
    classifier = LLMIntentClassifier(llm=mock_llm, intent_nodes=[dummy_node], confidence_threshold=0.6)
    result = await classifier.classify("ambiguous question")
    assert result.needs_guidance is True


@pytest.mark.asyncio
async def test_vector_channel_searches_store():
    mock_store = AsyncMock()
    mock_llm = AsyncMock()
    mock_store.search = AsyncMock(
        return_value=[RetrievedChunk(content="result", score=0.9, document_id="d1")]
    )
    mock_llm.embed = AsyncMock(return_value=[[0.1] * 10])

    channel = VectorSearchChannel(vector_store=mock_store, llm=mock_llm)
    results = await channel.search("query", IntentResult(), top_k=5)

    assert len(results) == 1
    assert results[0].content == "result"


@pytest.mark.asyncio
async def test_deduplication_removes_duplicate_content():
    processor = DeduplicationProcessor()
    chunks = [
        RetrievedChunk(content="same text", score=0.9),
        RetrievedChunk(content="same text", score=0.8),
        RetrievedChunk(content="different text", score=0.7),
    ]
    result = await processor.process(chunks)
    assert len(result) == 2
    assert result[0].content == "same text"
    assert result[0].score == 0.9  # keeps higher score


def test_prompt_builder_includes_query_and_chunks():
    builder = PromptBuilder(system_prompt="You are a helpful assistant.")
    history = ConversationHistory()
    chunks = [RetrievedChunk(content="Context chunk", score=0.9)]
    messages = builder.build(
        query="What is X?",
        history=history,
        retrieved=chunks,
        intents=[IntentResult()],
    )
    combined = " ".join(str(m) for m in messages)
    assert "What is X?" in combined
    assert "Context chunk" in combined
