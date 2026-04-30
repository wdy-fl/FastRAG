from __future__ import annotations
from typing import Protocol
from backend.core.models.ingestion import ChunkerSettings, IngestionContext
from backend.core.models.knowledge import DocumentChunk
from backend.core.exceptions import IngestionError


class ChunkerStrategy(Protocol):
    async def chunk(
        self, text: str, config: ChunkerSettings
    ) -> list[DocumentChunk]: ...


class ChunkerNode:
    name = "chunker"

    def __init__(self, strategies: dict[str, ChunkerStrategy]) -> None:
        self._strategies = strategies

    async def execute(
        self, context: IngestionContext, config: ChunkerSettings
    ) -> IngestionContext:
        strategy = self._strategies.get(config.chunker_type)
        if not strategy:
            raise IngestionError(f"Unknown chunker strategy: {config.chunker_type}")
        if context.parsed_text is None:
            raise IngestionError("ChunkerNode requires parsed_text")
        context.chunks = await strategy.chunk(
            context.enhanced_text or context.parsed_text, config
        )
        return context
