from __future__ import annotations
from fastrag.core.models.ingestion import ChunkerSettings
from fastrag.core.models.knowledge import DocumentChunk


class FixedSizeChunker:
    async def chunk(
        self, text: str, config: ChunkerSettings
    ) -> list[DocumentChunk]:
        size = config.chunk_size
        overlap = config.overlap
        step = max(size - overlap, 1)
        chunks: list[DocumentChunk] = []
        for i, start in enumerate(range(0, max(len(text), 1), step)):
            segment = text[start : start + size]
            if not segment:
                break
            chunks.append(DocumentChunk(content=segment, chunk_index=i))
        return chunks
