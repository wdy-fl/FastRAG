import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.core.rag.rewrite import LLMQueryRewriter
from backend.core.rag.intent import LLMIntentClassifier
from backend.core.rag.retrieve import (
    MultiChannelRetriever, VectorSearchChannel,
    QuestionSearchChannel, RrfProcessor,
)
from backend.infra.search.keyword import KeywordSearchChannel
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
    results = await channel.search("query", IntentResult(), top_k=5, query_vector=[0.1] * 10)

    assert len(results) == 1
    assert results[0].content == "result"



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


@pytest.mark.asyncio
async def test_question_channel_calls_search_questions():
    mock_store = AsyncMock()
    mock_llm = AsyncMock()
    mock_store.search_questions = AsyncMock(
        return_value=[RetrievedChunk(content="question result", score=0.85, document_id="d1")]
    )
    mock_llm.embed = AsyncMock(return_value=[[0.1] * 10])

    channel = QuestionSearchChannel(vector_store=mock_store, llm=mock_llm)
    results = await channel.search("退款多久？", IntentResult(), top_k=5, query_vector=[0.1] * 10)

    mock_store.search_questions.assert_awaited_once()
    assert len(results) == 1
    assert results[0].content == "question result"


@pytest.mark.asyncio
async def test_keyword_channel_searches_by_tsquery():
    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    channel = KeywordSearchChannel(session_factory=mock_session_factory)
    results = await channel.search("退款政策", IntentResult(), top_k=5, query_vector=[0.1] * 10)

    mock_session.execute.assert_awaited_once()
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_rrf_processor_merges_and_deduplicates():
    processor = RrfProcessor()
    channel_results = [
        [
            RetrievedChunk(content="chunk A", score=0.9, document_id="d1"),
            RetrievedChunk(content="chunk B", score=0.8, document_id="d2"),
        ],
        [
            RetrievedChunk(content="chunk A", score=0.7, document_id="d1"),
            RetrievedChunk(content="chunk C", score=0.6, document_id="d3"),
        ],
    ]
    result = await processor.process(channel_results)

    contents = [c.content for c in result]
    assert contents.count("chunk A") == 1
    assert len(result) == 3
    assert result[0].content == "chunk A"


@pytest.mark.asyncio
async def test_multi_channel_retriever_uses_rrf():
    mock_channel = AsyncMock()
    mock_channel.search = AsyncMock(
        return_value=[RetrievedChunk(content="result", score=0.9, document_id="d1")]
    )
    retriever = MultiChannelRetriever(channels=[mock_channel], llm=None)
    results = await retriever.retrieve(["query"], [IntentResult()])

    assert len(results) == 1
    assert results[0].content == "result"


@pytest.mark.asyncio
async def test_classifier_loads_nodes_from_repo():
    mock_llm = MagicMock()
    mock_llm.stream = MagicMock(
        side_effect=lambda msgs, **kw: _make_stream('{"confidence": 0.9, "matched_id": "n1"}')
    )
    orm_node = MagicMock(
        id="n1", name="Finance", level="domain", parent_id=None,
        intent_type="kb", keywords=["finance"], description="",
        knowledge_base_id="kb-1",
    )
    # Ensure attributes return actual values, not MagicMock objects
    orm_node.id = "n1"
    orm_node.name = "Finance"
    orm_node.level = "domain"
    orm_node.parent_id = None
    orm_node.intent_type = "kb"
    orm_node.keywords = ["finance"]
    orm_node.description = ""
    orm_node.knowledge_base_id = "kb-1"
    mock_repo = AsyncMock()
    mock_repo.list_intent_nodes = AsyncMock(return_value=[orm_node])
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock()

    classifier = LLMIntentClassifier(
        llm=mock_llm, intent_repo=mock_repo, cache=mock_cache,
        confidence_threshold=0.6,
    )
    result = await classifier.classify("What is finance?")
    assert result.matched_node is not None
    assert result.matched_node.id == "n1"


@pytest.mark.asyncio
async def test_classifier_caches_nodes_in_redis():
    mock_llm = MagicMock()
    mock_llm.stream = MagicMock(
        side_effect=lambda msgs, **kw: _make_stream('{"confidence": 0.9, "matched_id": null}')
    )
    mock_repo = AsyncMock()
    mock_repo.list_intent_nodes = AsyncMock(return_value=[])
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock()

    classifier = LLMIntentClassifier(
        llm=mock_llm, intent_repo=mock_repo, cache=mock_cache,
        confidence_threshold=0.6,
    )
    await classifier.classify("test")
    mock_cache.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_classifier_reads_from_redis_cache():
    mock_llm = MagicMock()
    mock_repo = AsyncMock()
    cached_json = json.dumps([IntentNode(
        id="n1", name="test", level="domain", intent_type="kb",
        knowledge_base_id="kb-1",
    ).model_dump_json()])
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=cached_json)

    classifier = LLMIntentClassifier(
        llm=mock_llm, intent_repo=mock_repo, cache=mock_cache,
        confidence_threshold=0.6,
    )
    nodes = await classifier._load_nodes()
    assert len(nodes) == 1
    assert nodes[0].id == "n1"
    mock_repo.list_intent_nodes.assert_not_awaited()


@pytest.mark.asyncio
async def test_vector_channel_uses_provided_query_vector():
    mock_store = AsyncMock()
    mock_store.search = AsyncMock(return_value=[])
    channel = VectorSearchChannel(vector_store=mock_store, llm=AsyncMock())
    vec = [0.1] * 10
    await channel.search("query", IntentResult(), top_k=5, query_vector=vec)
    mock_store.search.assert_awaited_once_with(
        query_vector=vec, top_k=5, knowledge_base_id=None,
    )


@pytest.mark.asyncio
async def test_vector_channel_routes_to_specific_kb():
    mock_store = AsyncMock()
    mock_store.search = AsyncMock(return_value=[])
    channel = VectorSearchChannel(vector_store=mock_store, llm=AsyncMock())
    node = IntentNode(id="n1", name="Finance", level="domain", intent_type="kb", knowledge_base_id="kb-1")
    intent = IntentResult(matched_node=node, confidence=0.9)
    await channel.search("query", intent, top_k=5, query_vector=[0.1] * 10)
    mock_store.search.assert_awaited_once_with(
        query_vector=[0.1] * 10, top_k=5, knowledge_base_id="kb-1",
    )


@pytest.mark.asyncio
async def test_vector_channel_no_route_for_system_intent():
    mock_store = AsyncMock()
    mock_store.search = AsyncMock(return_value=[])
    channel = VectorSearchChannel(vector_store=mock_store, llm=AsyncMock())
    node = IntentNode(id="n1", name="Chat", level="domain", intent_type="system")
    intent = IntentResult(matched_node=node, confidence=0.9)
    await channel.search("query", intent, top_k=5, query_vector=[0.1] * 10)
    mock_store.search.assert_awaited_once_with(
        query_vector=[0.1] * 10, top_k=5, knowledge_base_id=None,
    )


@pytest.mark.asyncio
async def test_keyword_channel_uses_query_vector_param():
    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    channel = KeywordSearchChannel(session_factory=mock_session_factory)
    results = await channel.search("query", IntentResult(), top_k=5, query_vector=[0.1] * 10)
    assert isinstance(results, list)
