from __future__ import annotations
from uuid import uuid4
from sqlalchemy import select, delete as sa_delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models.intent import IntentNodeORM
from backend.infra.cache.redis import RedisCache


class IntentRepo:
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
                await self._cache.delete("intent:nodes")
            except Exception:
                pass

    async def list_intent_nodes(self) -> list[IntentNodeORM]:
        result = await self._session.execute(select(IntentNodeORM))
        return list(result.scalars().all())

    async def create_intent_node(
        self, name: str, level: str, parent_id: str | None,
        intent_type: str, keywords: list, description: str,
        knowledge_base_id: str | None = None,
    ) -> IntentNodeORM:
        node = IntentNodeORM(
            id=str(uuid4()), name=name, level=level, parent_id=parent_id,
            intent_type=intent_type, keywords=keywords, description=description,
            knowledge_base_id=knowledge_base_id,
        )
        self._session.add(node)
        await self._session.commit()
        await self._session.refresh(node)
        await self._invalidate_cache()
        return node

    async def update_intent_node(
        self, node_id: str, **fields,
    ) -> IntentNodeORM:
        node = await self._session.get(IntentNodeORM, node_id)
        if node is None:
            raise ValueError(f"IntentNode {node_id} not found")
        for key, value in fields.items():
            if hasattr(node, key):
                setattr(node, key, value)
        await self._session.commit()
        await self._session.refresh(node)
        await self._invalidate_cache()
        return node

    async def delete_intent_node(self, node_id: str) -> None:
        await self._session.execute(
            sa_delete(IntentNodeORM).where(IntentNodeORM.id == node_id)
        )
        await self._session.commit()
        await self._invalidate_cache()

    async def delete_intent_node_cascade(self, node_id: str) -> None:
        """递归删除节点及其所有子孙节点。"""
        await self._session.execute(text("""
            WITH RECURSIVE tree AS (
                SELECT id FROM intent_nodes WHERE id = :node_id
                UNION ALL
                SELECT n.id FROM intent_nodes n
                JOIN tree t ON n.parent_id = t.id
            )
            DELETE FROM intent_nodes WHERE id IN (SELECT id FROM tree)
        """), {"node_id": node_id})
        await self._session.commit()
        await self._invalidate_cache()
