"""Integration tests for LoginService."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from authcore.application.services.auth.login_service import (
    LoginPayload,
    LoginResult,
    LoginService,
)
from authcore.config import Settings
from authcore.domain.exceptions import (
    AccountLockedError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    LoginRateLimitedError,
)
from authcore.domain.models.user import UserEntity
from authcore.external.rate_limiter import LoginRateLimiter
from authcore.infrastructure.cache.redis_client import RedisClient
from authcore.infrastructure.database.repositories.audit_log_repository import AuditLogRepository
from authcore.infrastructure.database.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from authcore.infrastructure.database.repositories.user_repository import UserRepository
from authcore.infrastructure.tokens.jwt_service import JWTService


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=4)).decode()


async def _persist_user(
    session: AsyncSession,
    *,
    email: str = "user@test.com",
    password: str = "Secure1!",
    is_verified: bool = True,
    is_locked: bool = False,
    lockout_until: datetime | None = None,
    failed_attempts: int = 0,
) -> UserEntity:
    repo = UserRepository(session)
    entity = UserEntity(
        id=uuid.uuid4(),
        email=email,
        hashed_password=_hash(password),
        role="member",
        is_verified=is_verified,
        is_locked=is_locked,
        failed_attempts=failed_attempts,
        lockout_until=lockout_until,
        created_at=datetime.now(tz=UTC),
    )
    return await repo.save_entity(entity)


def _make_svc(
    db_session: AsyncSession,
    jwt_service: JWTService,
    redis_client: RedisClient,
    settings: Settings,
) -> LoginService:
    rate_limiter = LoginRateLimiter(redis_client, max_attempts=5)
    return LoginService(
        user_repo=UserRepository(db_session),
        token_repo=RefreshTokenRepository(db_session),
        audit_repo=AuditLogRepository(db_session),
        jwt_service=jwt_service,
        rate_limiter=rate_limiter,
        settings=settings,
    )


class TestLoginService:
    async def test_valid_credentials_return_tokens(
        self,
        db_session: AsyncSession,
        jwt_service: JWTService,
        redis_client: RedisClient,
        settings: Settings,
    ) -> None:
        await _persist_user(db_session, email="valid@test.com")
        svc = _make_svc(db_session, jwt_service, redis_client, settings)
        result = await svc.execute(
            LoginPayload(email="valid@test.com", password="Secure1!")
        )
        assert isinstance(result, LoginResult)
        assert result.access_token
        assert result.refresh_token
        assert result.token_type == "bearer"

    async def test_wrong_password_raises(
        self,
        db_session: AsyncSession,
        jwt_service: JWTService,
        redis_client: RedisClient,
        settings: Settings,
    ) -> None:
        await _persist_user(db_session, email="wrongpw@test.com")
        svc = _make_svc(db_session, jwt_service, redis_client, settings)
        with pytest.raises(InvalidCredentialsError):
            await svc.execute(LoginPayload(email="wrongpw@test.com", password="WrongPass1!"))

    async def test_unknown_email_raises(
        self,
        db_session: AsyncSession,
        jwt_service: JWTService,
        redis_client: RedisClient,
        settings: Settings,
    ) -> None:
        svc = _make_svc(db_session, jwt_service, redis_client, settings)
        with pytest.raises(InvalidCredentialsError):
            await svc.execute(LoginPayload(email="nobody@test.com", password="Secure1!"))

    async def test_unverified_email_raises(
        self,
        db_session: AsyncSession,
        jwt_service: JWTService,
        redis_client: RedisClient,
        settings: Settings,
    ) -> None:
        await _persist_user(db_session, email="unverified@test.com", is_verified=False)
        svc = _make_svc(db_session, jwt_service, redis_client, settings)
        with pytest.raises(EmailNotVerifiedError):
            await svc.execute(LoginPayload(email="unverified@test.com", password="Secure1!"))

    async def test_locked_account_raises(
        self,
        db_session: AsyncSession,
        jwt_service: JWTService,
        redis_client: RedisClient,
        settings: Settings,
    ) -> None:
        future = datetime.now(tz=UTC) + timedelta(minutes=15)
        await _persist_user(
            db_session,
            email="locked@test.com",
            is_locked=True,
            lockout_until=future,
        )
        svc = _make_svc(db_session, jwt_service, redis_client, settings)
        with pytest.raises(AccountLockedError):
            await svc.execute(LoginPayload(email="locked@test.com", password="Secure1!"))

    async def test_rate_limited_raises(
        self,
        db_session: AsyncSession,
        jwt_service: JWTService,
        redis_client: RedisClient,
        settings: Settings,
    ) -> None:
        # Pre-fill rate limit counter
        for _ in range(5):
            await redis_client.incr("authcore:login_fail:127.0.0.1:rl@test.com")

        svc = _make_svc(db_session, jwt_service, redis_client, settings)
        with pytest.raises(LoginRateLimitedError):
            await svc.execute(
                LoginPayload(email="rl@test.com", password="Secure1!", ip_address="127.0.0.1")
            )
