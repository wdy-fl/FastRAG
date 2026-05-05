from __future__ import annotations
from uuid import uuid4
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models.knowledge import QueryTermMappingORM
from backend.infra.cache.redis import RedisCache


class MappingRepo:
    def __init__(
        self,
        session: AsyncSession,
        cache: RedisCache | None = None,
    ) -> None:
        self._session = session
        self._cache = cache

    async def _invalidate_cache(self) -> None:
        if self._cache:
            try:
                await self._cache.delete("query_term:mappings")
            except Exception:
                pass

    async def list_mappings(self) -> list[QueryTermMappingORM]:
        result = await self._session.execute(select(QueryTermMappingORM))
        return list(result.scalars().all())

    async def create_mapping(
        self, source_term: str, target_term: str,
        knowledge_base_id: str | None = None,
    ) -> QueryTermMappingORM:
        m = QueryTermMappingORM(
            id=str(uuid4()),
            source_term=source_term,
            target_term=target_term,
            knowledge_base_id=knowledge_base_id,
        )
        self._session.add(m)
        await self._session.commit()
        await self._session.refresh(m)
        await self._invalidate_cache()
        return m

    async def delete_mapping(self, mapping_id: str) -> None:
        await self._session.execute(
            sa_delete(QueryTermMappingORM).where(QueryTermMappingORM.id == mapping_id)
        )
        await self._session.commit()
        await self._invalidate_cache()
