from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.core.ingestion.nodes.enricher import EnricherNode
from backend.core.models.ingestion import (
    EnricherSettings, ChunkEnrichTask, ChunkEnrichType,
    IngestionConfig, IngestionContext,
    FetcherSettings, ParserSettings, ChunkerSettings,
)
from backend.core.models.knowledge import DocumentChunk


def _make_context(chunks: list[DocumentChunk] | None = None) -> IngestionContext:
    config = IngestionConfig(
        fetcher=FetcherSettings(source_type="local", source_uri="/tmp/test.txt"),
        parser=ParserSettings(),
        chunker=ChunkerSettings(),
    )
    ctx = IngestionContext(pipeline_id="p1", task_id="t1", config=config)
    ctx.chunks = chunks or [
        DocumentChunk(content="First chunk content.", chunk_index=0),
        DocumentChunk(content="Second chunk content.", chunk_index=1),
    ]
    return ctx


@pytest.mark.asyncio
async def test_enricher_keywords_written_to_chunk_metadata():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value='["python", "code"]')
    node = EnricherNode(llm=llm)
    ctx = _make_context()
    settings = EnricherSettings(
        attach_document_metadata=False,
        tasks=[ChunkEnrichTask(type=ChunkEnrichType.KEYWORDS)],
    )
    result_ctx = await node.execute(ctx, settings)
    assert result_ctx.chunks[0].metadata.get("keywords") == ["python", "code"]
    assert result_ctx.chunks[1].metadata.get("keywords") == ["python", "code"]
    assert llm.chat.await_count == 2  # one per chunk


@pytest.mark.asyncio
async def test_enricher_summary_written_to_chunk_metadata():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value="A brief summary.")
    node = EnricherNode(llm=llm)
    ctx = _make_context()
    settings = EnricherSettings(
        attach_document_metadata=False,
        tasks=[ChunkEnrichTask(type=ChunkEnrichType.SUMMARY)],
    )
    result_ctx = await node.execute(ctx, settings)
    assert result_ctx.chunks[0].metadata.get("summary") == "A brief summary."


@pytest.mark.asyncio
async def test_enricher_attaches_document_metadata_when_enabled():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value='["kw"]')
    node = EnricherNode(llm=llm)
    ctx = _make_context()
    ctx.metadata = {"source": "test_doc"}
    settings = EnricherSettings(
        attach_document_metadata=True,
        tasks=[ChunkEnrichTask(type=ChunkEnrichType.KEYWORDS)],
    )
    result_ctx = await node.execute(ctx, settings)
    assert result_ctx.chunks[0].metadata.get("source") == "test_doc"


@pytest.mark.asyncio
async def test_enricher_skips_when_no_tasks():
    llm = MagicMock()
    llm.chat = AsyncMock()
    node = EnricherNode(llm=llm)
    ctx = _make_context()
    settings = EnricherSettings(tasks=[])
    await node.execute(ctx, settings)
    llm.chat.assert_not_awaited()
