from __future__ import annotations
from typing import Protocol
from backend.core.models.ingestion import FetcherSettings, IngestionContext
from backend.core.exceptions import IngestionError


class FetcherStrategy(Protocol):
    async def fetch(self, settings: FetcherSettings) -> bytes: ...


class FetcherNode:
    name = "fetcher"

    def __init__(self, strategies: dict[str, FetcherStrategy]) -> None:
        self._strategies = strategies

    async def execute(
        self, context: IngestionContext, config: FetcherSettings
    ) -> IngestionContext:
        strategy = self._strategies.get(config.source_type)
        if not strategy:
            raise IngestionError(f"Unknown fetcher strategy: {config.source_type}")
        context.raw_content = await strategy.fetch(config)
        return context
