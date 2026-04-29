from __future__ import annotations
import re
from fastrag.core.models.ingestion import ChunkerSettings
from fastrag.core.models.knowledge import DocumentChunk

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


class StructureAwareChunker:
    """Splits text at Markdown heading boundaries. Falls back to paragraphs if no headings."""

    async def chunk(
        self, text: str, config: ChunkerSettings
    ) -> list[DocumentChunk]:
        boundaries = [m.start() for m in _HEADING_RE.finditer(text)]
        if not boundaries:
            # Fall back to paragraph splitting
            paragraphs = re.split(r"\n{2,}", text.strip())
            return [
                DocumentChunk(content=p.strip(), chunk_index=i)
                for i, p in enumerate(paragraphs)
                if p.strip()
            ]

        boundaries.append(len(text))
        segments: list[str] = []
        for i in range(len(boundaries) - 1):
            segment = text[boundaries[i] : boundaries[i + 1]].strip()
            if segment:
                segments.append(segment)

        return [
            DocumentChunk(content=seg, chunk_index=i)
            for i, seg in enumerate(segments)
        ]
