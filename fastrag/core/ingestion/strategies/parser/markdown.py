from __future__ import annotations
from fastrag.core.models.ingestion import ParserSettings


class MarkdownParser:
    async def parse(
        self, content: bytes, filename: str, config: ParserSettings
    ) -> str:
        return content.decode("utf-8", errors="replace")
