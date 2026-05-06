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
async def test_indexer_does_not_inject_keywords_str():
    """IndexerNode 不应再注入 _keywords_str 到 metadata。"""
    mock_llm = AsyncMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1] * 1024])
    mock_store = AsyncMock()
    mock_store.upsert = AsyncMock()

    node = IndexerNode(llm=mock_llm, vector_store=mock_store)
    ctx = _make_context()
    await node.execute(ctx, IndexerSettings())

    call_args = mock_store.upsert.call_args
    chunks_arg = call_args[0][0]
    assert "_keywords_str" not in chunks_arg[0].chunk.metadata


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


@pytest.mark.asyncio
async def test_indexer_calls_bm25_mark_dirty():
    """IndexerNode 应在入库完成后调用 bm25_manager.mark_dirty()。"""
    mock_llm = AsyncMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1] * 1024])
    mock_store = AsyncMock()
    mock_store.upsert = AsyncMock()

    mock_bm25 = MagicMock()
    mock_bm25.mark_dirty = MagicMock()

    node = IndexerNode(
        llm=mock_llm,
        vector_store=mock_store,
        bm25_manager=mock_bm25,
    )
    ctx = _make_context()
    await node.execute(ctx, IndexerSettings())

    mock_bm25.mark_dirty.assert_called_once()


@pytest.mark.asyncio
async def test_indexer_no_bm25_manager_no_error():
    """没有 bm25_manager 时 IndexerNode 不应报错。"""
    mock_llm = AsyncMock()
    mock_llm.embed = AsyncMock(return_value=[[0.1] * 1024])
    mock_store = AsyncMock()
    mock_store.upsert = AsyncMock()

    node = IndexerNode(llm=mock_llm, vector_store=mock_store)
    ctx = _make_context()
    # Should not raise
    await node.execute(ctx, IndexerSettings())
