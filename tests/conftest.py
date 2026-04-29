import asyncio
import os
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

from fastrag.db.models import Base

TEST_DATABASE_URL = os.getenv(
    "FASTRAG_TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/fastrag_test",
)


def _setup_db():
    """Create all tables synchronously using asyncio.run() before tests."""
    async def _create():
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()
    asyncio.run(_create())


def _teardown_db():
    """Drop all tables synchronously after tests."""
    async def _drop():
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
    asyncio.run(_drop())


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    _setup_db()
    yield
    _teardown_db()


@pytest.fixture
async def db_session(setup_db) -> AsyncSession:
    engine = create_async_engine(TEST_DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()
