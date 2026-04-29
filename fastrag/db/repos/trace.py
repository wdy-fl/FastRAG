from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastrag.db.models.trace import RagTraceRunORM, RagTraceNodeORM


class TraceRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_run(
        self, run_id: str, conversation_id: str, query: str
    ) -> RagTraceRunORM:
        run = RagTraceRunORM(
            id=run_id,
            conversation_id=conversation_id,
            query=query,
            status="running",
        )
        self._session.add(run)
        await self._session.commit()
        return run

    async def update_run(
        self, run_id: str, status: str, total_duration_ms: int
    ) -> None:
        run = await self._get_run_raw(run_id)
        if run:
            run.status = status
            run.total_duration_ms = total_duration_ms
            await self._session.commit()

    async def save_node(
        self,
        run_id: str,
        node_id: str,
        node_name: str,
        status: str,
        duration_ms: int,
        detail: dict | None = None,
    ) -> None:
        node = RagTraceNodeORM(
            id=node_id,
            run_id=run_id,
            node_name=node_name,
            status=status,
            duration_ms=duration_ms,
            detail=detail,
        )
        self._session.add(node)
        await self._session.commit()

    async def get_run(self, run_id: str) -> RagTraceRunORM | None:
        stmt = (
            select(RagTraceRunORM)
            .where(RagTraceRunORM.id == run_id)
            .options(selectinload(RagTraceRunORM.nodes))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_run_raw(self, run_id: str) -> RagTraceRunORM | None:
        stmt = select(RagTraceRunORM).where(RagTraceRunORM.id == run_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
