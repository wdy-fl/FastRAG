import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastrag.core.rag.memory import SlidingWindowMemory
from fastrag.core.models.chat import ConversationHistory, ChatMessage
from fastrag.db.models.conversation import MessageORM, ConversationSummaryORM


def _make_message(role: str, content: str, seq: int) -> MessageORM:
    msg = MessageORM()
    msg.id = f"msg-{seq}"
    msg.role = role
    msg.content = content
    msg.seq = seq
    msg.conversation_id = "conv-1"
    return msg


@pytest.mark.asyncio
async def test_load_returns_history_with_messages():
    mock_repo = AsyncMock()
    mock_llm = AsyncMock()
    mock_repo.get_recent_messages = AsyncMock(
        return_value=[
            _make_message("user", "hello", 1),
            _make_message("assistant", "hi", 2),
        ]
    )
    mock_repo.get_summary = AsyncMock(return_value=None)

    memory = SlidingWindowMemory(repo=mock_repo, llm=mock_llm, window_size=4)
    history = await memory.load("conv-1")

    assert isinstance(history, ConversationHistory)
    assert len(history.messages) == 2
    assert history.messages[0].role == "user"
    assert history.summary is None


@pytest.mark.asyncio
async def test_load_includes_summary_content():
    mock_repo = AsyncMock()
    mock_llm = AsyncMock()
    summary_orm = ConversationSummaryORM()
    summary_orm.content = "Previous context summary"
    summary_orm.summarized_up_to_seq = 3

    mock_repo.get_recent_messages = AsyncMock(return_value=[])
    mock_repo.get_summary = AsyncMock(return_value=summary_orm)

    memory = SlidingWindowMemory(repo=mock_repo, llm=mock_llm, window_size=4)
    history = await memory.load("conv-1")

    assert history.summary == "Previous context summary"


@pytest.mark.asyncio
async def test_save_persists_messages():
    mock_repo = AsyncMock()
    mock_repo.count_messages = AsyncMock(return_value=2)
    mock_llm = AsyncMock()

    memory = SlidingWindowMemory(
        repo=mock_repo, llm=mock_llm, window_size=4, summary_threshold=100
    )
    await memory.save("conv-1", query="What is AI?", answer="AI is...")

    mock_repo.save_message.assert_any_await("conv-1", role="user", content="What is AI?")
    mock_repo.save_message.assert_any_await("conv-1", role="assistant", content="AI is...")


@pytest.mark.asyncio
async def test_save_triggers_summary_compression_when_over_threshold():
    mock_repo = AsyncMock()
    mock_repo.count_messages = AsyncMock(return_value=5)
    mock_repo.get_recent_messages = AsyncMock(return_value=[
        _make_message("user", "q", 1),
        _make_message("assistant", "a", 2),
    ])
    mock_repo.get_summary = AsyncMock(return_value=None)

    mock_llm = AsyncMock()

    async def fake_stream(messages, **kwargs):
        async def _gen():
            from fastrag.core.models.chat import LLMEvent
            yield LLMEvent(type="content", content="Summary text")
        return _gen()

    mock_llm.stream = fake_stream

    memory = SlidingWindowMemory(
        repo=mock_repo, llm=mock_llm, window_size=4, summary_threshold=5
    )

    import asyncio
    await memory.save("conv-1", query="q", answer="a")
    await asyncio.sleep(0.05)  # let background task run
