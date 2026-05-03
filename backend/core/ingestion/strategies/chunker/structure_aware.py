from __future__ import annotations
import re
from backend.core.models.ingestion import ChunkerSettings
from backend.core.models.knowledge import DocumentChunk

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_FENCE_RE = re.compile(r"^```", re.MULTILINE)


def _split_into_sections(text: str) -> list[str]:
    """按 Markdown heading 边界切节，保留 heading 在对应节内。"""
    boundaries = [m.start() for m in _HEADING_RE.finditer(text)]
    if not boundaries:
        return [text] if text.strip() else []
    boundaries.append(len(text))
    sections = []
    for i in range(len(boundaries) - 1):
        seg = text[boundaries[i]: boundaries[i + 1]].strip()
        if seg:
            sections.append(seg)
    return sections


def _paragraph_sub_chunk(text: str, chunk_size: int, overlap: int) -> list[str]:
    """段落子分块降级，返回 str 列表。"""
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text.strip()) if p.strip()]
    if not paragraphs:
        return [text] if text.strip() else []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        if current and current_len + len(para) > chunk_size:
            chunks.append("\n\n".join(current))
            kept: list[str] = []
            total = 0
            for p in reversed(current):
                if total + len(p) > overlap:
                    break
                kept.insert(0, p)
                total += len(p)
            current, current_len = kept, total
        current.append(para)
        current_len += len(para)

    if current:
        chunks.append("\n\n".join(current))

    return chunks


class StructureAwareChunker:
    """三档控制 + code fence 保护 + 超长节子分块降级。"""

    async def chunk(
        self, text: str, config: ChunkerSettings
    ) -> list[DocumentChunk]:
        min_chars = config.min_chars
        target_chars = config.target_chars
        max_chars = config.max_chars
        chunk_size = config.chunk_size
        overlap = config.overlap

        sections = _split_into_sections(text)
        if not sections:
            return []

        output_texts: list[str] = []
        current_parts: list[str] = []
        current_len = 0

        def flush() -> None:
            if current_parts:
                output_texts.append("\n\n".join(current_parts))
                current_parts.clear()

        for section in sections:
            slen = len(section)

            if slen > max_chars:
                flush()
                current_len = 0
                sub_chunks = _paragraph_sub_chunk(section, chunk_size, overlap)
                output_texts.extend(sub_chunks)
                continue

            if current_len >= min_chars and current_len + slen > target_chars:
                flush()
                current_len = 0

            current_parts.append(section)
            current_len += slen

        flush()

        # code fence 保护：确保 ``` 不被跨 chunk 分割
        merged: list[str] = []
        i = 0
        while i < len(output_texts):
            t = output_texts[i]
            while t.count("```") % 2 != 0 and i + 1 < len(output_texts):
                i += 1
                t = t + "\n\n" + output_texts[i]
            merged.append(t)
            i += 1

        return [
            DocumentChunk(content=t.strip(), chunk_index=idx)
            for idx, t in enumerate(merged)
            if t.strip()
        ]
