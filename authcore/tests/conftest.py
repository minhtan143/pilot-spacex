"""Shared pytest fixtures for AuthCore test suite."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from authcore.config import Settings
from authcore.domain.services.password_policy import PasswordPolicy
from authcore.infrastructure.cache.redis_client import RedisClient
from authcore.infrastructure.database.base import Base
from authcore.infrastructure.database.models.audit_log import AuditLogModel  # noqa: F401
from authcore.infrastructure.database.models.refresh_token import RefreshTokenModel  # noqa: F401
from authcore.infrastructure.database.models.user import UserModel  # noqa: F401
from authcore.infrastructure.database.repositories.audit_log_repository import AuditLogRepository
from authcore.infrastructure.database.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from authcore.infrastructure.database.repositories.user_repository import UserRepository
from authcore.infrastructure.tokens.jwt_service import JWTService
from authcore.infrastructure.tokens.key_manager import KeyManager


# ---------------------------------------------------------------------------
# RSA key pair (generated once per process)
# ---------------------------------------------------------------------------

def _generate_rsa_pem_pair() -> tuple[str, str]:
    """Generate a 2048-bit RSA key pair and return (private_pem, public_pem) strings."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


_PRIVATE_PEM, _PUBLIC_PEM = _generate_rsa_pem_pair()


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def settings() -> Settings:
    """Test settings using SQLite in-memory + fake RSA keys."""
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",  # type: ignore[arg-type]  # test-only override
        redis_url="redis://localhost:6379/15",
        jwt_private_key=SecretStr(_PRIVATE_PEM),
        jwt_public_key=_PUBLIC_PEM,
        access_token_expire_minutes=15,
        refresh_token_expire_days=7,
    )


# ---------------------------------------------------------------------------
# Database engine + tables (session-scoped — created once)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def engine(settings: Settings):  # type: ignore[return]
    """Create async SQLite engine and initialise all tables."""
    eng = create_async_engine(
        str(settings.database_url),
        connect_args={"check_same_thread": False},
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:  # type: ignore[no-untyped-def]
    """Per-test async session that rolls back after each test."""
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        await session.begin()
        try:
            yield session
        finally:
            await session.rollback()


# ---------------------------------------------------------------------------
# Redis stub — in-memory dict, no real Redis required
# ---------------------------------------------------------------------------

class _StubRedisClient(RedisClient):
    """In-memory Redis stub for unit/integration tests."""

    def __init__(self) -> None:  # type: ignore[override]
        self._store: dict[str, str] = {}
        self._ttls: dict[str, int] = {}

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        self._store[key] = value
        if ex is not None:
            self._ttls[key] = ex
        return True

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def delete(self, key: str) -> bool:
        self._store.pop(key, None)
        self._ttls.pop(key, None)
        return True

    async def exists(self, key: str) -> bool:
        return key in self._store

    async def incr(self, key: str) -> int:
        current = int(self._store.get(key, "0"))
        new_val = current + 1
        self._store[key] = str(new_val)
        return new_val

    async def expire(self, key: str, seconds: int) -> None:
        self._ttls[key] = seconds

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        pass


@pytest.fixture
def redis_client() -> _StubRedisClient:
    """Fresh in-memory Redis stub per test."""
    return _StubRedisClient()


# ---------------------------------------------------------------------------
# Domain services
# ---------------------------------------------------------------------------

@pytest.fixture
def password_policy() -> PasswordPolicy:
    """PasswordPolicy instance."""
    return PasswordPolicy()


# ---------------------------------------------------------------------------
# JWT / KeyManager
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def key_manager(settings: Settings) -> KeyManager:
    """KeyManager loaded from test RSA key pair."""
    return KeyManager(settings)


@pytest.fixture(scope="session")
def jwt_service(key_manager: KeyManager, settings: Settings) -> JWTService:
    """JWTService wired to test KeyManager and settings."""
    return JWTService(key_manager, settings)


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------

@pytest.fixture
def user_repository(db_session: AsyncSession) -> UserRepository:
    """UserRepository wired to per-test db_session."""
    return UserRepository(db_session)


@pytest.fixture
def refresh_token_repository(db_session: AsyncSession) -> RefreshTokenRepository:
    """RefreshTokenRepository wired to per-test db_session."""
    return RefreshTokenRepository(db_session)


@pytest.fixture
def audit_log_repository(db_session: AsyncSession) -> AuditLogRepository:
    """AuditLogRepository wired to per-test db_session."""
    return AuditLogRepository(db_session)
