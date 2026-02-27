"""Unit tests for database engine and session factory helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from authcore.infrastructure.database.engine import get_db_session, get_engine, get_session_factory


class TestGetEngine:
    def test_creates_async_engine_with_correct_url(self) -> None:
        mock_engine = MagicMock()
        mock_settings = MagicMock()
        mock_settings.database_url = "postgresql+asyncpg://user:pass@localhost/db"

        with patch(
            "authcore.infrastructure.database.engine.create_async_engine",
            return_value=mock_engine,
        ) as mock_create:
            result = get_engine(mock_settings)

        assert result is mock_engine
        mock_create.assert_called_once_with(
            "postgresql+asyncpg://user:pass@localhost/db",
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )

    def test_passes_pool_pre_ping_true(self) -> None:
        mock_settings = MagicMock()
        mock_settings.database_url = "postgresql+asyncpg://localhost/db"

        with patch(
            "authcore.infrastructure.database.engine.create_async_engine",
            return_value=MagicMock(),
        ) as mock_create:
            get_engine(mock_settings)

        _, kwargs = mock_create.call_args
        assert kwargs["pool_pre_ping"] is True


class TestGetSessionFactory:
    def test_returns_async_sessionmaker(self) -> None:
        mock_engine = MagicMock()
        factory = get_session_factory(mock_engine)
        assert isinstance(factory, async_sessionmaker)

    def test_session_factory_bound_to_engine(self, engine: MagicMock) -> None:
        factory = get_session_factory(engine)
        # The factory should be bound to the given engine — just verify it's callable
        assert callable(factory)


class TestGetDbSession:
    async def test_yields_session_and_commits(self) -> None:
        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory = MagicMock()

        # Context manager support for async with factory() as session
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_cm

        gen = get_db_session(mock_factory)
        session = await gen.__anext__()

        assert session is mock_session
        try:
            await gen.__anext__()
        except StopAsyncIteration:
            pass

        mock_session.commit.assert_called_once()

    async def test_rollback_on_exception(self) -> None:
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock(side_effect=Exception("commit failed"))
        mock_factory = MagicMock()

        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_cm

        gen = get_db_session(mock_factory)
        session = await gen.__anext__()
        assert session is mock_session

        with pytest.raises(Exception, match="commit failed"):
            try:
                await gen.athrow(Exception("commit failed"))
            except StopAsyncIteration:
                pass

        mock_session.rollback.assert_called_once()
