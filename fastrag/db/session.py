from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_session_factory(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 20,
) -> async_sessionmaker[AsyncSession]:
    engine: AsyncEngine = create_async_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
    )
    return async_sessionmaker(engine, expire_on_commit=False)
