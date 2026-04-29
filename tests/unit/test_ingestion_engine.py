import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastrag.core.ingestion.engine import IngestionEngine
from fastrag.core.ingestion.nodes.fetcher import FetcherNode
from fastrag.core.ingestion.nodes.parser import ParserNode
from fastrag.core.ingestion.nodes.chunker import ChunkerNode
from fastrag.core.ingestion.nodes.indexer import IndexerNode
from fastrag.core.models.ingestion import (
    IngestionConfig, IngestionContext, FetcherSettings, ParserSettings, ChunkerSettings
)
from fastrag.core.models.knowledge import DocumentChunk


def _make_config(source_type="local"):
    return IngestionConfig(
        fetcher=FetcherSettings(source_type=source_type, source_uri="/tmp/a.pdf"),
        parser=ParserSettings(),
        chunker=ChunkerSettings(chunker_type="fixed", chunk_size=100, overlap=0),
    )


def _make_context(config):
    return IngestionContext(pipeline_id="p1", task_id="t1", config=config)


@pytest.mark.asyncio
async def test_engine_executes_all_steps_in_order():
    mock_fetcher = AsyncMock()
    mock_parser = AsyncMock()
    mock_chunker = AsyncMock()
    mock_indexer = AsyncMock()

    async def fetcher_exec(ctx, cfg):
        ctx.raw_content = b"bytes"
        return ctx

    async def parser_exec(ctx, cfg):
        ctx.parsed_text = "text"
        return ctx

    async def chunker_exec(ctx, cfg):
        ctx.chunks = [DocumentChunk(content="chunk", chunk_index=0)]
        return ctx

    async def indexer_exec(ctx, cfg):
        return ctx

    mock_fetcher.execute = fetcher_exec
    mock_parser.execute = parser_exec
    mock_chunker.execute = chunker_exec
    mock_indexer.execute = indexer_exec

    engine = IngestionEngine(nodes={
        "fetcher": mock_fetcher,
        "parser": mock_parser,
        "enhancer": None,
        "chunker": mock_chunker,
        "enricher": None,
        "indexer": mock_indexer,
    })

    config = _make_config()
    context = _make_context(config)
    result = await engine.execute(config, context)

    assert result.raw_content == b"bytes"
    assert result.parsed_text == "text"
    assert len(result.chunks) == 1
    node_names = [r.node_name for r in result.node_results]
    assert "fetcher" in node_names
    assert "parser" in node_names
    assert "chunker" in node_names


@pytest.mark.asyncio
async def test_engine_skips_none_optional_nodes():
    mock_fetcher = AsyncMock()

    async def fetcher_exec(ctx, cfg):
        ctx.raw_content = b"data"
        return ctx

    mock_fetcher.execute = fetcher_exec
    mock_parser = AsyncMock()

    async def parser_exec(ctx, cfg):
        ctx.parsed_text = "text"
        return ctx

    mock_parser.execute = parser_exec
    mock_chunker = AsyncMock()

    async def chunker_exec(ctx, cfg):
        return ctx

    mock_chunker.execute = chunker_exec
    mock_indexer = AsyncMock()

    async def indexer_exec(ctx, cfg):
        return ctx

    mock_indexer.execute = indexer_exec

    engine = IngestionEngine(nodes={
        "fetcher": mock_fetcher,
        "parser": mock_parser,
        "enhancer": None,
        "chunker": mock_chunker,
        "enricher": None,
        "indexer": mock_indexer,
    })

    config = _make_config()
    context = _make_context(config)
    result = await engine.execute(config, context)

    skipped = [r for r in result.node_results if r.status == "skipped"]
    assert len(skipped) == 2  # enhancer + enricher skipped


@pytest.mark.asyncio
async def test_engine_records_failure_and_raises():
    from fastrag.core.exceptions import IngestionError

    mock_fetcher = AsyncMock()

    async def failing_fetch(ctx, cfg):
        raise IngestionError("fetch failed")

    mock_fetcher.execute = failing_fetch

    engine = IngestionEngine(nodes={
        "fetcher": mock_fetcher,
        "parser": MagicMock(),
        "enhancer": None,
        "chunker": MagicMock(),
        "enricher": None,
        "indexer": MagicMock(),
    })

    config = _make_config()
    context = _make_context(config)
    with pytest.raises(IngestionError, match="fetch failed"):
        await engine.execute(config, context)

    assert context.node_results[0].status == "failed"
    assert "fetch failed" in context.node_results[0].error
