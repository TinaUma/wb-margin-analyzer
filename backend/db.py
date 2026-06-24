from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.config import get_settings


@lru_cache
def get_engine():
    return create_async_engine(
        get_settings().DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory():
    return async_sessionmaker(
        get_engine(),
        expire_on_commit=False,
        autoflush=False,
        class_=AsyncSession,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        try:
            yield session
        except BaseException:
            await session.rollback()
            raise
