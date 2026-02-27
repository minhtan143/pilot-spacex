"""Integration tests for RegisterService."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from authcore.application.services.auth.register_service import (
    RegisterPayload,
    RegisterResult,
    RegisterService,
)
from authcore.config import Settings
from authcore.domain.exceptions import EmailExistsError, PasswordWeakError
from authcore.infrastructure.cache.redis_client import RedisClient
from authcore.infrastructure.database.repositories.user_repository import UserRepository


def _make_svc(
    db_session: AsyncSession,
    redis_client: RedisClient,
    settings: Settings,
    email_service: AsyncMock | None = None,
) -> RegisterService:
    if email_service is None:
        email_service = AsyncMock()
    return RegisterService(
        user_repo=UserRepository(db_session),
        redis_client=redis_client,
        email_service=email_service,
        settings=settings,
    )


class TestRegisterService:
    async def test_register_new_user_succeeds(
        self, db_session: AsyncSession, redis_client: RedisClient, settings: Settings
    ) -> None:
        svc = _make_svc(db_session, redis_client, settings)
        result = await svc.execute(
            RegisterPayload(email="new@test.com", password="Secure1!")
        )
        assert isinstance(result, RegisterResult)
        assert result.email == "new@test.com"
        assert result.user_id is not None

    async def test_register_sends_verification_token_to_redis(
        self, db_session: AsyncSession, redis_client: RedisClient, settings: Settings
    ) -> None:
        svc = _make_svc(db_session, redis_client, settings)
        await svc.execute(RegisterPayload(email="token@test.com", password="Secure1!"))
        # At least one key starting with authcore:verify: should be in store
        verify_keys = [k for k in redis_client._store if k.startswith("authcore:verify:")]  # type: ignore[attr-defined]
        assert len(verify_keys) >= 1

    async def test_register_duplicate_email_raises(
        self, db_session: AsyncSession, redis_client: RedisClient, settings: Settings
    ) -> None:
        svc = _make_svc(db_session, redis_client, settings)
        await svc.execute(RegisterPayload(email="dup@test.com", password="Secure1!"))
        with pytest.raises(EmailExistsError):
            await svc.execute(RegisterPayload(email="dup@test.com", password="Secure1!"))

    async def test_register_weak_password_raises(
        self, db_session: AsyncSession, redis_client: RedisClient, settings: Settings
    ) -> None:
        svc = _make_svc(db_session, redis_client, settings)
        with pytest.raises(PasswordWeakError):
            await svc.execute(RegisterPayload(email="weak@test.com", password="abc"))

    async def test_register_email_failure_still_returns_result(
        self, db_session: AsyncSession, redis_client: RedisClient, settings: Settings
    ) -> None:
        failing_email = AsyncMock()
        failing_email.send_verification.side_effect = Exception("SMTP error")
        svc = _make_svc(db_session, redis_client, settings, failing_email)
        result = await svc.execute(
            RegisterPayload(email="emailfail@test.com", password="Secure1!")
        )
        # Should succeed with verification_sent=False
        assert result.verification_sent is False
        assert result.user_id is not None
