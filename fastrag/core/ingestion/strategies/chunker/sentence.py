from __future__ import annotations
import re
from fastrag.core.models.ingestion import ChunkerSettings
from fastrag.core.models.knowledge import DocumentChunk


class SentenceChunker:
    async def chunk(
        self, text: str, config: ChunkerSettings
    ) -> list[DocumentChunk]:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        return [
            DocumentChunk(content=s.strip(), chunk_index=i)
            for i, s in enumerate(sentences)
            if s.strip()
        ]
