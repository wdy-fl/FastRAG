import pytest
from backend.core.ingestion.strategies.chunker.fixed import FixedSizeChunker
from backend.core.ingestion.strategies.chunker.paragraph import ParagraphChunker
from backend.core.ingestion.strategies.chunker.structure_aware import StructureAwareChunker
from backend.core.models.ingestion import ChunkerSettings


@pytest.mark.asyncio
async def test_fixed_size_chunker_splits_long_text():
    chunker = FixedSizeChunker()
    config = ChunkerSettings(chunker_type="fixed", chunk_size=50, overlap=10)
    text = "a" * 200
    chunks = await chunker.chunk(text, config)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.content) <= 60  # chunk_size + some tolerance


@pytest.mark.asyncio
async def test_fixed_size_chunker_preserves_overlap():
    chunker = FixedSizeChunker()
    config = ChunkerSettings(chunker_type="fixed", chunk_size=20, overlap=5)
    text = "0123456789" * 10
    chunks = await chunker.chunk(text, config)
    # Verify overlap: end of chunk[0] should appear at start of chunk[1]
    assert chunks[0].content[-5:] == chunks[1].content[:5]


@pytest.mark.asyncio
async def test_paragraph_chunker_splits_on_blank_lines():
    chunker = ParagraphChunker()
    config = ChunkerSettings(chunker_type="paragraph")
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = await chunker.chunk(text, config)
    assert len(chunks) == 3
    assert chunks[0].content == "First paragraph."
    assert chunks[1].content == "Second paragraph."


@pytest.mark.asyncio
async def test_structure_aware_chunker_splits_on_headings():
    chunker = StructureAwareChunker()
    config = ChunkerSettings(chunker_type="structure_aware")
    text = "# Section 1\nContent one.\n\n## Section 1.1\nDetail.\n\n# Section 2\nContent two."
    chunks = await chunker.chunk(text, config)
    assert len(chunks) >= 2
    assert any("Section 1" in c.content for c in chunks)
    assert any("Section 2" in c.content for c in chunks)


@pytest.mark.asyncio
async def test_fixed_chunker_assigns_sequential_indices():
    chunker = FixedSizeChunker()
    config = ChunkerSettings(chunker_type="fixed", chunk_size=10, overlap=0)
    text = "x" * 50
    chunks = await chunker.chunk(text, config)
    indices = [c.chunk_index for c in chunks]
    assert indices == list(range(len(chunks)))
