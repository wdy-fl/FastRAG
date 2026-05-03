from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.core.ingestion.nodes.enhancer import EnhancerNode
from backend.core.models.ingestion import (
    EnhancerSettings, EnhanceTask, EnhanceTaskType,
    IngestionConfig, IngestionContext,
    FetcherSettings, ParserSettings, ChunkerSettings, IndexerSettings,
)


def _make_context(parsed_text: str = "Hello world. This is a test.") -> IngestionContext:
    config = IngestionConfig(
        fetcher=FetcherSettings(source_type="local", source_uri="/tmp/test.txt"),
        parser=ParserSettings(),
        chunker=ChunkerSettings(),
    )
    return IngestionContext(pipeline_id="p1", task_id="t1", config=config, parsed_text=parsed_text)


@pytest.mark.asyncio
async def test_enhancer_keywords_writes_to_context():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value='["AI", "test"]')
    node = EnhancerNode(llm=llm)
    ctx = _make_context()
    settings = EnhancerSettings(tasks=[EnhanceTask(type=EnhanceTaskType.KEYWORDS)])
    result_ctx = await node.execute(ctx, settings)
    assert result_ctx.keywords == ["AI", "test"]
    llm.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_enhancer_context_enhance_writes_enhanced_text():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value="Enhanced text content.")
    node = EnhancerNode(llm=llm)
    ctx = _make_context()
    settings = EnhancerSettings(tasks=[EnhanceTask(type=EnhanceTaskType.CONTEXT_ENHANCE)])
    result_ctx = await node.execute(ctx, settings)
    assert result_ctx.enhanced_text == "Enhanced text content."


@pytest.mark.asyncio
async def test_enhancer_skips_when_no_tasks():
    llm = MagicMock()
    llm.chat = AsyncMock()
    node = EnhancerNode(llm=llm)
    ctx = _make_context()
    settings = EnhancerSettings(tasks=[])
    result_ctx = await node.execute(ctx, settings)
    llm.chat.assert_not_awaited()
    assert result_ctx.keywords == []


@pytest.mark.asyncio
async def test_enhancer_questions_writes_to_context():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value='["What is this?", "How does it work?"]')
    node = EnhancerNode(llm=llm)
    ctx = _make_context()
    settings = EnhancerSettings(tasks=[EnhanceTask(type=EnhanceTaskType.QUESTIONS)])
    result_ctx = await node.execute(ctx, settings)
    assert "What is this?" in result_ctx.questions


@pytest.mark.asyncio
async def test_enhancer_metadata_merges_into_context():
    llm = MagicMock()
    llm.chat = AsyncMock(return_value='{"author": "Alice", "year": 2026}')
    node = EnhancerNode(llm=llm)
    ctx = _make_context()
    settings = EnhancerSettings(tasks=[EnhanceTask(type=EnhanceTaskType.METADATA)])
    result_ctx = await node.execute(ctx, settings)
    assert result_ctx.metadata.get("author") == "Alice"
