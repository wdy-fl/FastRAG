from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models.ingestion import IngestionTaskORM


class IngestionTaskRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, kb_id: str, document_id: str) -> IngestionTaskORM:
        task = IngestionTaskORM(
            id=str(uuid4()),
            knowledge_base_id=kb_id,
            document_id=document_id,
            status="pending",
            node_results=[],
        )
        self._session.add(task)
        await self._session.commit()
        await self._session.refresh(task)
        return task

    async def get(self, task_id: str) -> IngestionTaskORM | None:
        result = await self._session.execute(
            select(IngestionTaskORM).where(IngestionTaskORM.id == task_id)
        )
        return result.scalar_one_or_none()

    async def get_by_document(self, document_id: str) -> IngestionTaskORM | None:
        result = await self._session.execute(
            select(IngestionTaskORM)
            .where(IngestionTaskORM.document_id == document_id)
            .order_by(IngestionTaskORM.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_started(self, task_id: str) -> None:
        task = await self.get(task_id)
        if task:
            task.status = "running"
            task.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await self._session.commit()

    async def append_node_result(
        self, task_id: str, node_name: str, status: str, duration_ms: int
    ) -> None:
        task = await self.get(task_id)
        if task:
            results = list(task.node_results or [])
            results.append({"node_name": node_name, "status": status, "duration_ms": duration_ms})
            task.node_results = results
            await self._session.commit()

    async def update_completed(self, task_id: str, chunk_count: int) -> None:
        task = await self.get(task_id)
        if task:
            task.status = "completed"
            task.chunk_count = chunk_count
            task.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await self._session.commit()

    async def delete_by_document(self, document_id: str) -> None:
        from sqlalchemy import delete
        await self._session.execute(
            delete(IngestionTaskORM).where(IngestionTaskORM.document_id == document_id)
        )
        await self._session.commit()

    async def update_failed(self, task_id: str, error: str) -> None:
        task = await self.get(task_id)
        if task:
            task.status = "failed"
            task.error_message = error
            task.finished_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await self._session.commit()
