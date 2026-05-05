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
