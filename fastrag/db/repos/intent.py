from __future__ import annotations
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastrag.db.models.intent import IntentNodeORM


class IntentRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_intent_nodes(self) -> list[IntentNodeORM]:
        result = await self._session.execute(select(IntentNodeORM))
        return list(result.scalars().all())

    async def create_intent_node(
        self, name: str, level: str, parent_id: str | None,
        intent_type: str, keywords: list, description: str
    ) -> IntentNodeORM:
        node = IntentNodeORM(
            id=str(uuid4()), name=name, level=level, parent_id=parent_id,
            intent_type=intent_type, keywords=keywords, description=description,
        )
        self._session.add(node)
        await self._session.commit()
        await self._session.refresh(node)
        return node

    async def delete_intent_node(self, node_id: str) -> None:
        from sqlalchemy import delete
        await self._session.execute(
            delete(IntentNodeORM).where(IntentNodeORM.id == node_id)
        )
        await self._session.commit()
