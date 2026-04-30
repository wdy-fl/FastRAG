from __future__ import annotations
import re
from backend.core.models.ingestion import ChunkerSettings
from backend.core.models.knowledge import DocumentChunk


class ParagraphChunker:
    async def chunk(
        self, text: str, config: ChunkerSettings
    ) -> list[DocumentChunk]:
        paragraphs = re.split(r"\n{2,}", text.strip())
        return [
            DocumentChunk(content=p.strip(), chunk_index=i)
            for i, p in enumerate(paragraphs)
            if p.strip()
        ]
