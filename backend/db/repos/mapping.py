from __future__ import annotations
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models.knowledge import QueryTermMappingORM


class MappingRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_mappings(self) -> list[QueryTermMappingORM]:
        result = await self._session.execute(select(QueryTermMappingORM))
        return list(result.scalars().all())

    async def create_mapping(
        self, source_term: str, target_term: str,
        knowledge_base_id: str | None = None
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
        return m

    async def delete_mapping(self, mapping_id: str) -> None:
        from sqlalchemy import delete
        await self._session.execute(
            delete(QueryTermMappingORM).where(QueryTermMappingORM.id == mapping_id)
        )
        await self._session.commit()
