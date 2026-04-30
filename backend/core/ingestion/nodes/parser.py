from __future__ import annotations
from typing import Protocol
from backend.core.models.ingestion import ParserSettings, IngestionContext
from backend.core.exceptions import IngestionError


class ParserStrategy(Protocol):
    async def parse(
        self, content: bytes, filename: str, config: ParserSettings
    ) -> str: ...


class ParserNode:
    name = "parser"

    def __init__(self, strategies: dict[str, ParserStrategy]) -> None:
        self._strategies = strategies

    async def execute(
        self, context: IngestionContext, config: ParserSettings
    ) -> IngestionContext:
        strategy = self._strategies.get(config.parser_type)
        if not strategy:
            raise IngestionError(f"Unknown parser strategy: {config.parser_type}")
        filename = context.metadata.get("filename", "unknown")
        if context.raw_content is None:
            raise IngestionError("ParserNode requires raw_content to be set by FetcherNode")
        context.parsed_text = await strategy.parse(
            context.raw_content, filename, config
        )
        return context
