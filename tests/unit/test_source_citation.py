import pytest
from backend.core.models.chat import SourceItem, SourcesEvent, ChatEvent


def test_source_item_creation():
    item = SourceItem(
        ref=1,
        document_id="doc-abc",
        document_name="员工手册.pdf",
        score=0.92,
        content="年假天数根据工龄确定",
    )
    assert item.ref == 1
    assert item.document_name == "员工手册.pdf"


def test_source_item_optional_fields():
    item = SourceItem(ref=1, score=0.5, content="some text")
    assert item.document_id is None
    assert item.document_name is None


def test_sources_event_type():
    event = SourcesEvent(
        sources=[
            SourceItem(ref=1, document_id="d1", document_name="a.pdf", score=0.9, content="x"),
        ]
    )
    assert event.type == "sources"
    assert len(event.sources) == 1


def test_sources_event_empty():
    event = SourcesEvent(sources=[])
    assert event.type == "sources"
    assert event.sources == []


def test_sources_event_in_chat_event_union():
    """SourcesEvent must be part of ChatEvent union so isinstance checks work."""
    event = SourcesEvent(sources=[])
    assert isinstance(event, ChatEvent.__args__[-1])  # last type added to union


from backend.core.rag.prompt import PromptBuilder, _DEFAULT_SYSTEM
from backend.core.models.chat import ConversationHistory, RetrievedChunk


def test_default_prompt_contains_citation_instruction():
    assert "[1]" in _DEFAULT_SYSTEM or "bracket number" in _DEFAULT_SYSTEM.lower()


def test_prompt_builder_includes_citation_instruction():
    builder = PromptBuilder()
    messages = builder.build(
        query="test?",
        history=ConversationHistory(),
        retrieved=[
            RetrievedChunk(content="chunk1", score=0.9, document_id="d1"),
        ],
        intents=[],
    )
    system_msg = messages[0]["content"]
    assert "bracket number" in system_msg.lower() or "[1]" in system_msg


from unittest.mock import AsyncMock, MagicMock
from backend.db.repos.knowledge import KnowledgeRepo


@pytest.mark.asyncio
async def test_batch_get_names_returns_mapping():
    mock_session = AsyncMock()
    # Simulate SQLAlchemy result: list of Row objects with .id and .filename
    row1 = MagicMock()
    row1.id = "doc-1"
    row1.filename = "员工手册.pdf"
    row2 = MagicMock()
    row2.id = "doc-2"
    row2.filename = "休假制度.docx"
    mock_result = AsyncMock()
    mock_result.__iter__ = MagicMock(return_value=iter([row1, row2]))
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = KnowledgeRepo(session=mock_session)
    result = await repo.batch_get_names(["doc-1", "doc-2"])

    assert result == {"doc-1": "员工手册.pdf", "doc-2": "休假制度.docx"}


@pytest.mark.asyncio
async def test_batch_get_names_empty_input():
    mock_session = AsyncMock()
    repo = KnowledgeRepo(session=mock_session)
    result = await repo.batch_get_names([])

    assert result == {}
    mock_session.execute.assert_not_awaited()


# ---------------------------------------------------------------------------
# Task 4: RAGPipeline yields SourcesEvent
# ---------------------------------------------------------------------------
from backend.core.models.chat import ChatRequest, RetrievedChunk, ConversationHistory
from backend.core.rag.pipeline import RAGPipeline


def _make_pipeline(doc_name_map: dict[str, str] | None = None) -> RAGPipeline:
    """Build a minimal RAGPipeline with mocked deps for sources testing."""
    mock_llm = AsyncMock()
    mock_memory = AsyncMock()
    mock_rewriter = AsyncMock()
    mock_intent_classifier = AsyncMock()
    mock_retriever = AsyncMock()
    mock_prompt_builder = AsyncMock()
    mock_tracer = AsyncMock()
    mock_doc_repo = AsyncMock()

    mock_retriever.retrieve = AsyncMock(return_value=[])
    mock_memory.load = AsyncMock(return_value=ConversationHistory())
    mock_rewriter.rewrite = AsyncMock(return_value="rewritten")
    mock_rewriter.split = AsyncMock(return_value=["sub-q"])

    # matched_node must not be None so the pipeline proceeds to retrieval
    mock_node = MagicMock(intent_type="qa")
    mock_intent_classifier.classify = AsyncMock(
        return_value=MagicMock(needs_guidance=False, matched_node=mock_node, confidence=0.5)
    )

    mock_prompt_builder.build = MagicMock(return_value=[{"role": "user", "content": "q"}])
    mock_tracer.start_run = AsyncMock()
    mock_tracer.finish_run = AsyncMock()
    mock_tracer.trace_node = lambda name: (lambda fn: fn)  # passthrough

    if doc_name_map is not None:
        mock_doc_repo.batch_get_names = AsyncMock(return_value=doc_name_map)

    return RAGPipeline(
        llm=mock_llm,
        memory=mock_memory,
        rewriter=mock_rewriter,
        intent_classifier=mock_intent_classifier,
        retriever=mock_retriever,
        prompt_builder=mock_prompt_builder,
        tracer=mock_tracer,
        doc_repo=mock_doc_repo,
    )


@pytest.mark.asyncio
async def test_pipeline_yields_sources_event_with_retrieved_chunks():
    pipeline = _make_pipeline(doc_name_map={"doc-1": "员工手册.pdf"})

    pipeline._retriever.retrieve = AsyncMock(return_value=[
        RetrievedChunk(content="年假5天", score=0.9, document_id="doc-1"),
    ])

    async def fake_stream(messages, **kwargs):
        from backend.core.models.chat import LLMEvent
        yield LLMEvent(type="content", content="年假5天[1]")
        yield LLMEvent(type="done", content="")
    pipeline._llm.stream = fake_stream

    events = []
    async for event in pipeline.chat(ChatRequest(query="年假几天?", conversation_id="c1")):
        events.append(event)

    sources_events = [e for e in events if isinstance(e, SourcesEvent)]
    assert len(sources_events) == 1
    assert sources_events[0].sources[0].ref == 1
    assert sources_events[0].sources[0].document_name == "员工手册.pdf"
    assert sources_events[0].sources[0].score == 0.9


@pytest.mark.asyncio
async def test_pipeline_yields_empty_sources_when_no_retrieval():
    pipeline = _make_pipeline(doc_name_map={})

    pipeline._retriever.retrieve = AsyncMock(return_value=[])

    async def fake_stream(messages, **kwargs):
        from backend.core.models.chat import LLMEvent
        yield LLMEvent(type="content", content="未检索到相关信息")
        yield LLMEvent(type="done", content="")
    pipeline._llm.stream = fake_stream

    events = []
    async for event in pipeline.chat(ChatRequest(query="???", conversation_id="c1")):
        events.append(event)

    sources_events = [e for e in events if isinstance(e, SourcesEvent)]
    assert len(sources_events) == 1
    assert sources_events[0].sources == []


@pytest.mark.asyncio
async def test_pipeline_sources_event_comes_before_llm_content():
    pipeline = _make_pipeline(doc_name_map={"doc-1": "a.pdf"})

    pipeline._retriever.retrieve = AsyncMock(return_value=[
        RetrievedChunk(content="x", score=0.8, document_id="doc-1"),
    ])

    async def fake_stream(messages, **kwargs):
        from backend.core.models.chat import LLMEvent
        yield LLMEvent(type="content", content="answer")
        yield LLMEvent(type="done", content="")
    pipeline._llm.stream = fake_stream

    events = []
    async for event in pipeline.chat(ChatRequest(query="q", conversation_id="c1")):
        events.append(event)

    types = [e.type if hasattr(e, 'type') else None for e in events]
    assert types.index("sources") < types.index("content")
