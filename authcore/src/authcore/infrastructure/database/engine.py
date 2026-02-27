"""Async database engine and session factory for AuthCore."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from authcore.config import Settings


def get_engine(settings: Settings) -> AsyncEngine:
    """Create async SQLAlchemy engine from settings.

    Args:
        settings: Application settings.

    Returns:
        Configured async engine.
    """
    return create_async_engine(
        str(settings.database_url),
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )


def get_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session factory bound to engine.

    Args:
        engine: Async SQLAlchemy engine.

    Returns:
        Configured async session maker.
    """
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Async generator yielding database sessions with auto commit/rollback.

    Args:
        session_factory: Async session maker to create sessions from.

    Yields:
        AsyncSession with automatic commit on success and rollback on error.
    """
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
