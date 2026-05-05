from __future__ import annotations
import json
import re
from backend.core.models.mapping import QueryTermMapping
from backend.infra.cache.redis import RedisCache


class QueryTermMapper:
    def __init__(
        self,
        mapping_repo: "MappingRepo | None" = None,
        cache: RedisCache | None = None,
    ) -> None:
        self._repo = mapping_repo
        self._cache = cache

    async def _load_mappings(self) -> list[QueryTermMapping]:
        if self._repo is None:
            return []

        CACHE_KEY = "query_term:mappings"
        if self._cache:
            try:
                cached = await self._cache.get(CACHE_KEY)
                if cached:
                    return [
                        QueryTermMapping.model_validate_json(m)
                        for m in json.loads(cached)
                    ]
            except Exception:
                pass

        orm_mappings = await self._repo.list_mappings()
        mappings = [
            QueryTermMapping(
                id=m.id, source_term=m.source_term,
                target_term=m.target_term,
                knowledge_base_id=m.knowledge_base_id,
            )
            for m in orm_mappings
        ]

        if self._cache:
            try:
                payload = json.dumps([m.model_dump_json() for m in mappings])
                await self._cache.set(CACHE_KEY, payload, ttl=7200)
            except Exception:
                pass

        return mappings

    async def expand(self, query: str, kb_id: str | None = None) -> str:
        mappings = await self._load_mappings()
        result = query
        for m in mappings:
            if m.knowledge_base_id is None or m.knowledge_base_id == kb_id:
                pattern = r'\b' + re.escape(m.source_term) + r'\b'
                result = re.sub(pattern, m.target_term, result)
        return result
