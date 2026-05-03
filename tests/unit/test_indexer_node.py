import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.core.ingestion.nodes.indexer import IndexerNode
from backend.core.models.ingestion import IndexerSettings, IngestionContext, IngestionConfig
from backend.core.models.ingestion import FetcherSettings, ParserSettings, ChunkerSettings
from backend.core.models.knowledge import DocumentChunk


def _make_context(chunks=None, questions=None):
    config = IngestionConfig(
        fetcher=FetcherSettings(source_type="local", source_uri="/tmp/test.txt"),
        parser=ParserSettings(),
        chunker=ChunkerSettings(),
    )
    ctx = IngestionContext(pipeline_id="p1", task_id="t1", config=config)
    ctx.chunks = chunks or [
        DocumentChunk(
            content="chunk text",
            chunk_index=0,
            metadata={"keywords": ["退款", "政策", "30日"]},
        )
    ]
    ctx.questions = questions or []
    ctx.metadata = {"knowledge_base_id": "kb-1", "document_id": "doc-1"}
    return ctx


@pytest.mark.asyncio
async def test_indexer_injects_keywords_str_into_metadata():
    mock_llm = AsyncMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1] * 1024])
    mock_store = AsyncMock()
    mock_store.upsert = AsyncMock()

    node = IndexerNode(llm=mock_llm, vector_store=mock_store)
    ctx = _make_context()
    await node.execute(ctx, IndexerSettings())

    call_args = mock_store.upsert.call_args
    chunks_arg = call_args[0][0]
    assert chunks_arg[0].chunk.metadata.get("_keywords_str") == "退款 政策 30日"


@pytest.mark.asyncio
async def test_indexer_persists_questions_when_present():
    mock_llm = AsyncMock()
    mock_llm.embed = AsyncMock(side_effect=[
        [[0.1] * 1024],                    # chunks embed
        [[0.2] * 1024, [0.3] * 1024],      # questions embed
    ])
    mock_store = AsyncMock()
    mock_store.upsert = AsyncMock()

    mock_session = AsyncMock()
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

    node = IndexerNode(llm=mock_llm, vector_store=mock_store, session_factory=mock_session_factory)
    ctx = _make_context(questions=["退款多久？", "如何申请退款？"])
    await node.execute(ctx, IndexerSettings())

    assert mock_llm.embed.call_count == 2
    assert mock_session.add.call_count == 2
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_indexer_skips_questions_when_empty():
    mock_llm = AsyncMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1] * 1024])
    mock_store = AsyncMock()
    mock_store.upsert = AsyncMock()

    node = IndexerNode(llm=mock_llm, vector_store=mock_store, session_factory=None)
    ctx = _make_context(questions=[])
    await node.execute(ctx, IndexerSettings())

    assert mock_llm.embed.call_count == 1  # only chunks, no questions
