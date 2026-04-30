from __future__ import annotations
from backend.core.models.ingestion import FetcherSettings
from backend.infra.storage.s3 import S3Storage


class S3Fetcher:
    def __init__(self, storage: S3Storage) -> None:
        self._storage = storage

    async def fetch(self, settings: FetcherSettings) -> bytes:
        # source_uri format: s3://bucket/key  or just key
        key = settings.source_uri.split("/", 3)[-1] if "://" in settings.source_uri else settings.source_uri
        return await self._storage.download(key)
