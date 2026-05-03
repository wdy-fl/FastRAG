from __future__ import annotations
import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from backend.db.models.base import Base
from backend.db.models.ingestion import IngestionTaskORM
from backend.db.models.knowledge import KnowledgeBaseORM, KnowledgeDocumentORM
from backend.db.repos.ingestion_task import IngestionTaskRepo


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        # seed KB and document
        kb = KnowledgeBaseORM(id="kb1", name="KB1", description="", ingestion_config={})
        doc = KnowledgeDocumentORM(
            id="doc1", knowledge_base_id="kb1",
            filename="test.txt", source_type="local",
            source_uri="/tmp/test.txt", status="pending", chunk_count=0,
        )
        s.add(kb)
        s.add(doc)
        await s.commit()
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_get_task(session):
    repo = IngestionTaskRepo(session)
    task = await repo.create(kb_id="kb1", document_id="doc1")
    assert task.id is not None
    assert task.status == "pending"

    fetched = await repo.get(task.id)
    assert fetched is not None
    assert fetched.document_id == "doc1"


@pytest.mark.asyncio
async def test_update_started(session):
    repo = IngestionTaskRepo(session)
    task = await repo.create(kb_id="kb1", document_id="doc1")
    await repo.update_started(task.id)
    fetched = await repo.get(task.id)
    assert fetched.status == "running"
    assert fetched.started_at is not None


@pytest.mark.asyncio
async def test_update_completed(session):
    repo = IngestionTaskRepo(session)
    task = await repo.create(kb_id="kb1", document_id="doc1")
    await repo.update_completed(task.id, chunk_count=42)
    fetched = await repo.get(task.id)
    assert fetched.status == "completed"
    assert fetched.chunk_count == 42
    assert fetched.finished_at is not None


@pytest.mark.asyncio
async def test_update_failed(session):
    repo = IngestionTaskRepo(session)
    task = await repo.create(kb_id="kb1", document_id="doc1")
    await repo.update_failed(task.id, error="boom")
    fetched = await repo.get(task.id)
    assert fetched.status == "failed"
    assert fetched.error_message == "boom"


@pytest.mark.asyncio
async def test_get_by_document(session):
    repo = IngestionTaskRepo(session)
    task = await repo.create(kb_id="kb1", document_id="doc1")
    fetched = await repo.get_by_document("doc1")
    assert fetched is not None
    assert fetched.id == task.id
