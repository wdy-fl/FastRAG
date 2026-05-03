from __future__ import annotations
import re
from backend.core.models.ingestion import ChunkerSettings
from backend.core.models.knowledge import DocumentChunk


def _trim_to_overlap(units: list[str], overlap: int) -> tuple[list[str], int]:
    """从末尾倒推，保留不超过 overlap 字符的 units 作为下一块的起始。"""
    kept: list[str] = []
    total = 0
    for unit in reversed(units):
        if total + len(unit) > overlap:
            break
        kept.insert(0, unit)
        total += len(unit)
    return kept, total


class ParagraphChunker:
    async def chunk(
        self, text: str, config: ChunkerSettings
    ) -> list[DocumentChunk]:
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text.strip()) if p.strip()]
        if not paragraphs:
            return []

        chunk_size = config.chunk_size
        overlap = config.overlap
        chunks: list[DocumentChunk] = []
        current: list[str] = []
        current_len = 0
        idx = 0

        for para in paragraphs:
            if current and current_len + len(para) > chunk_size:
                chunks.append(DocumentChunk(content="\n\n".join(current), chunk_index=idx))
                idx += 1
                current, current_len = _trim_to_overlap(current, overlap)
            current.append(para)
            current_len += len(para)

        if current:
            chunks.append(DocumentChunk(content="\n\n".join(current), chunk_index=idx))

        return chunks
