from __future__ import annotations
import asyncio
from backend.core.models.ingestion import FetcherSettings


class LocalFileFetcher:
    async def fetch(self, settings: FetcherSettings) -> bytes:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _read_file, settings.source_uri)


def _read_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()
