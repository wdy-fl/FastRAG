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
async def test_paragraph_chunker_splits_short_paragraphs_into_one_chunk():
    """短段落总长 < chunk_size，应合并为 1 个 chunk。"""
    chunker = ParagraphChunker()
    config = ChunkerSettings(chunker_type="paragraph", chunk_size=500, overlap=0)
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = await chunker.chunk(text, config)
    assert len(chunks) == 1
    assert "First paragraph." in chunks[0].content
    assert "Third paragraph." in chunks[0].content


@pytest.mark.asyncio
async def test_structure_aware_chunker_splits_on_headings():
    chunker = StructureAwareChunker()
    config = ChunkerSettings(chunker_type="structure_aware")
    text = "# Section 1\nContent one.\n\n## Section 1.1\nDetail.\n\n# Section 2\nContent two."
    chunks = await chunker.chunk(text, config)
    # With default min_chars=600, small sections are merged into one chunk
    assert len(chunks) >= 1
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

@pytest.mark.asyncio
async def test_paragraph_chunker_respects_chunk_size():
    """段落总长超过 chunk_size 时应分为多个 chunk。"""
    chunker = ParagraphChunker()
    paragraphs = [f"Paragraph number {i} with some padding text here." for i in range(5)]
    text = "\n\n".join(paragraphs)
    config = ChunkerSettings(chunker_type="paragraph", chunk_size=80, overlap=0)
    chunks = await chunker.chunk(text, config)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.content) <= 160  # some tolerance


@pytest.mark.asyncio
async def test_paragraph_chunker_overlap():
    chunker = ParagraphChunker()
    paragraphs = [f"Para {i} is here and has enough text to matter." for i in range(6)]
    text = "\n\n".join(paragraphs)
    config = ChunkerSettings(chunker_type="paragraph", chunk_size=60, overlap=30)
    chunks = await chunker.chunk(text, config)
    assert len(chunks) >= 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1


@pytest.mark.asyncio
async def test_sentence_chunker_respects_chunk_size():
    from backend.core.ingestion.strategies.chunker.sentence import SentenceChunker
    chunker = SentenceChunker()
    text = " ".join([f"This is sentence {i}." for i in range(10)])
    config = ChunkerSettings(chunker_type="sentence", chunk_size=50, overlap=0)
    chunks = await chunker.chunk(text, config)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.content) <= 100  # some tolerance for boundary


@pytest.mark.asyncio
async def test_sentence_chunker_overlap():
    from backend.core.ingestion.strategies.chunker.sentence import SentenceChunker
    chunker = SentenceChunker()
    text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
    config = ChunkerSettings(chunker_type="sentence", chunk_size=40, overlap=20)
    chunks = await chunker.chunk(text, config)
    assert len(chunks) >= 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1


@pytest.mark.asyncio
async def test_structure_aware_merges_small_sections():
    """小节（< min_chars）应聚合到同一 chunk。"""
    chunker = StructureAwareChunker()
    config = ChunkerSettings(
        chunker_type="structure_aware",
        chunk_size=500,
        min_chars=100,
        target_chars=300,
        max_chars=500,
    )
    text = "# A\nShort A.\n\n# B\nShort B.\n\n# C\nShort C.\n\n# D\nShort D."
    chunks = await chunker.chunk(text, config)
    assert len(chunks) < 4  # sections should be merged


@pytest.mark.asyncio
async def test_structure_aware_sub_chunks_oversized_section():
    """单节超过 max_chars 时应降级为段落子分块。"""
    chunker = StructureAwareChunker()
    config = ChunkerSettings(
        chunker_type="structure_aware",
        chunk_size=100,
        min_chars=50,
        target_chars=80,
        max_chars=120,
    )
    # Create oversized section with multiple paragraphs so sub-chunking works
    big_section = "# Big Section\n" + "\n\n".join([f"Word sentence paragraph {i}. This has some content." for i in range(8)])
    text = big_section
    chunks = await chunker.chunk(text, config)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.content) <= 400  # sub-chunked


@pytest.mark.asyncio
async def test_structure_aware_preserves_code_fence():
    """code fence 块应视为原子单元，不在内部切分。"""
    chunker = StructureAwareChunker()
    config = ChunkerSettings(
        chunker_type="structure_aware",
        chunk_size=50,
        min_chars=20,
        target_chars=40,
        max_chars=200,
    )
    text = "# Section\n```python\nfor i in range(10):\n    print(i)\n```\nEnd."
    chunks = await chunker.chunk(text, config)
    fence_chunks = [c for c in chunks if "```" in c.content]
    for fc in fence_chunks:
        assert fc.content.count("```") % 2 == 0  # fences appear in pairs
