from __future__ import annotations
import httpx
from backend.core.models.ingestion import FetcherSettings


class HttpUrlFetcher:
    async def fetch(self, settings: FetcherSettings) -> bytes:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(settings.source_uri)
            resp.raise_for_status()
            return resp.content
