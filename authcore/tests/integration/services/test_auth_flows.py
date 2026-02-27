"""Integration tests for verify, refresh, logout, password reset flows."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import bcrypt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from authcore.application.services.auth.change_password_service import (
    ChangePasswordPayload,
    ChangePasswordService,
)
from authcore.application.services.auth.forgot_password_service import (
    ForgotPasswordPayload,
    ForgotPasswordService,
)
from authcore.application.services.auth.logout_all_service import LogoutAllPayload, LogoutAllService
from authcore.application.services.auth.logout_service import LogoutPayload, LogoutService
from authcore.application.services.auth.refresh_token_service import (
    RefreshTokenPayload,
    RefreshTokenService,
)
from authcore.application.services.auth.resend_verification_service import (
    ResendVerificationPayload,
    ResendVerificationService,
)
from authcore.application.services.auth.reset_password_service import (
    ResetPasswordPayload,
    ResetPasswordService,
)
from authcore.application.services.auth.verify_email_service import (
    VerifyEmailPayload,
    VerifyEmailService,
)
from authcore.config import Settings
from authcore.domain.exceptions import (
    AlreadyVerifiedError,
    PasswordMismatchError,
    PasswordWeakError,
    ResendRateLimitedError,
    TokenFamilyRevokedError,
    TokenInvalidError,
)
from authcore.domain.models.refresh_token import RefreshTokenEntity
from authcore.domain.models.user import UserEntity
from authcore.infrastructure.cache.redis_client import RedisClient
from authcore.infrastructure.database.repositories.audit_log_repository import AuditLogRepository
from authcore.infrastructure.database.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from authcore.infrastructure.database.repositories.user_repository import UserRepository
from authcore.infrastructure.tokens.jwt_service import JWTService


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=4)).decode()


async def _make_user(
    session: AsyncSession,
    email: str = "u@test.com",
    is_verified: bool = True,
) -> UserEntity:
    repo = UserRepository(session)
    entity = UserEntity(
        id=uuid.uuid4(),
        email=email,
        hashed_password=_hash("Secure1!"),
        role="member",
        is_verified=is_verified,
        is_locked=False,
        failed_attempts=0,
        lockout_until=None,
        created_at=datetime.now(tz=UTC),
    )
    return await repo.save_entity(entity)


async def _make_refresh_token(
    session: AsyncSession,
    user_id: uuid.UUID,
    jwt_service: JWTService,
    settings: Settings,
    *,
    is_revoked: bool = False,
) -> tuple[str, RefreshTokenEntity]:
    raw, hsh = jwt_service.create_refresh_token_pair()
    entity = RefreshTokenEntity(
        id=uuid.uuid4(),
        user_id=user_id,
        token_hash=hsh,
        family_id=uuid.uuid4(),
        is_revoked=is_revoked,
        expires_at=datetime.now(tz=UTC) + timedelta(days=settings.refresh_token_expire_days),
        created_at=datetime.now(tz=UTC),
    )
    repo = RefreshTokenRepository(session)
    stored = await repo.create_token(entity)
    return raw, stored


class TestVerifyEmailService:
    async def test_valid_token_verifies_user(
        self, db_session: AsyncSession, redis_client: RedisClient
    ) -> None:
        user = await _make_user(db_session, is_verified=False)
        token = "validtoken123"
        await redis_client.set(f"authcore:verify:{token}", str(user.id))

        svc = VerifyEmailService(UserRepository(db_session), redis_client)
        result = await svc.execute(VerifyEmailPayload(token=token))
        assert result.user_id == user.id

    async def test_invalid_token_raises(
        self, db_session: AsyncSession, redis_client: RedisClient
    ) -> None:
        svc = VerifyEmailService(UserRepository(db_session), redis_client)
        with pytest.raises(TokenInvalidError):
            await svc.execute(VerifyEmailPayload(token="notexist"))

    async def test_already_verified_raises(
        self, db_session: AsyncSession, redis_client: RedisClient
    ) -> None:
        user = await _make_user(db_session, email="already@test.com", is_verified=True)
        token = "alreadytok"
        await redis_client.set(f"authcore:verify:{token}", str(user.id))
        svc = VerifyEmailService(UserRepository(db_session), redis_client)
        with pytest.raises(AlreadyVerifiedError):
            await svc.execute(VerifyEmailPayload(token=token))

    async def test_token_consumed_after_verification(
        self, db_session: AsyncSession, redis_client: RedisClient
    ) -> None:
        user = await _make_user(
            db_session, email="consume@test.com", is_verified=False
        )
        token = "consumetoken"
        await redis_client.set(f"authcore:verify:{token}", str(user.id))
        svc = VerifyEmailService(UserRepository(db_session), redis_client)
        await svc.execute(VerifyEmailPayload(token=token))
        assert not await redis_client.exists(f"authcore:verify:{token}")


class TestRefreshTokenService:
    async def test_valid_refresh_issues_new_tokens(
        self,
        db_session: AsyncSession,
        jwt_service: JWTService,
        redis_client: RedisClient,  # noqa: ARG002
        settings: Settings,
    ) -> None:
        user = await _make_user(db_session, email="refresh@test.com")
        raw, _ = await _make_refresh_token(db_session, user.id, jwt_service, settings)

        svc = RefreshTokenService(
            user_repo=UserRepository(db_session),
            token_repo=RefreshTokenRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
            jwt_service=jwt_service,
            settings=settings,
        )
        result = await svc.execute(RefreshTokenPayload(raw_refresh_token=raw))
        assert result.access_token
        assert result.refresh_token != raw

    async def test_revoked_token_triggers_family_revocation(
        self,
        db_session: AsyncSession,
        jwt_service: JWTService,
        redis_client: RedisClient,  # noqa: ARG002
        settings: Settings,
    ) -> None:
        user = await _make_user(db_session, email="reuse@test.com")
        raw, _ = await _make_refresh_token(
            db_session, user.id, jwt_service, settings, is_revoked=True
        )
        svc = RefreshTokenService(
            user_repo=UserRepository(db_session),
            token_repo=RefreshTokenRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
            jwt_service=jwt_service,
            settings=settings,
        )
        with pytest.raises(TokenFamilyRevokedError):
            await svc.execute(RefreshTokenPayload(raw_refresh_token=raw))

    async def test_unknown_token_raises(
        self,
        db_session: AsyncSession,
        jwt_service: JWTService,
        settings: Settings,
    ) -> None:
        svc = RefreshTokenService(
            user_repo=UserRepository(db_session),
            token_repo=RefreshTokenRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
            jwt_service=jwt_service,
            settings=settings,
        )
        with pytest.raises(TokenInvalidError):
            await svc.execute(RefreshTokenPayload(raw_refresh_token="nosuchtoken"))


class TestLogoutService:
    async def test_logout_revokes_token(
        self,
        db_session: AsyncSession,
        jwt_service: JWTService,
        redis_client: RedisClient,
        settings: Settings,
    ) -> None:
        user = await _make_user(db_session, email="logout@test.com")
        raw, stored = await _make_refresh_token(db_session, user.id, jwt_service, settings)

        svc = LogoutService(
            token_repo=RefreshTokenRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
            redis_client=redis_client,
            settings=settings,
        )
        result = await svc.execute(
            LogoutPayload(
                raw_refresh_token=raw,
                jti=str(uuid.uuid4()),
                user_id=user.id,
            )
        )
        assert result.logged_out is True

    async def test_logout_blacklists_jti(
        self,
        db_session: AsyncSession,
        jwt_service: JWTService,
        redis_client: RedisClient,
        settings: Settings,
    ) -> None:
        user = await _make_user(db_session, email="jtiblacklist@test.com")
        raw, _ = await _make_refresh_token(db_session, user.id, jwt_service, settings)
        jti = str(uuid.uuid4())

        svc = LogoutService(
            token_repo=RefreshTokenRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
            redis_client=redis_client,
            settings=settings,
        )
        await svc.execute(LogoutPayload(raw_refresh_token=raw, jti=jti, user_id=user.id))
        assert await redis_client.exists(f"authcore:jti_blacklist:{jti}")


class TestLogoutAllService:
    async def test_logout_all_revokes_all_tokens(
        self,
        db_session: AsyncSession,
        jwt_service: JWTService,
        settings: Settings,
    ) -> None:
        user = await _make_user(db_session, email="logoutall@test.com")
        await _make_refresh_token(db_session, user.id, jwt_service, settings)
        await _make_refresh_token(db_session, user.id, jwt_service, settings)

        svc = LogoutAllService(
            token_repo=RefreshTokenRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
        )
        result = await svc.execute(LogoutAllPayload(user_id=user.id))
        assert result.revoked is True


class TestChangePasswordService:
    async def test_valid_change_succeeds(self, db_session: AsyncSession) -> None:
        user = await _make_user(db_session, email="changepw@test.com")
        svc = ChangePasswordService(
            user_repo=UserRepository(db_session),
            token_repo=RefreshTokenRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
        )
        result = await svc.execute(
            ChangePasswordPayload(
                user_id=user.id,
                current_password="Secure1!",
                new_password="NewSecure2@",
            )
        )
        assert result.changed is True

    async def test_wrong_current_password_raises(self, db_session: AsyncSession) -> None:
        user = await _make_user(db_session, email="wrongcurrent@test.com")
        svc = ChangePasswordService(
            user_repo=UserRepository(db_session),
            token_repo=RefreshTokenRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
        )
        with pytest.raises(PasswordMismatchError):
            await svc.execute(
                ChangePasswordPayload(
                    user_id=user.id,
                    current_password="WrongPass1!",
                    new_password="NewSecure2@",
                )
            )

    async def test_weak_new_password_raises(self, db_session: AsyncSession) -> None:
        user = await _make_user(db_session, email="weaknew@test.com")
        svc = ChangePasswordService(
            user_repo=UserRepository(db_session),
            token_repo=RefreshTokenRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
        )
        with pytest.raises(PasswordWeakError):
            await svc.execute(
                ChangePasswordPayload(
                    user_id=user.id,
                    current_password="Secure1!",
                    new_password="weak",
                )
            )


class TestForgotAndResetPassword:
    async def test_forgot_password_always_returns_accepted(
        self, db_session: AsyncSession, redis_client: RedisClient, settings: Settings
    ) -> None:
        email_svc = AsyncMock()
        svc = ForgotPasswordService(
            user_repo=UserRepository(db_session),
            redis_client=redis_client,
            email_service=email_svc,
            settings=settings,
        )
        result = await svc.execute(ForgotPasswordPayload(email="nobody@test.com"))
        assert result.accepted is True

    async def test_forgot_password_stores_token_for_existing_user(
        self, db_session: AsyncSession, redis_client: RedisClient, settings: Settings
    ) -> None:
        await _make_user(db_session, email="forgotpw@test.com")
        email_svc = AsyncMock()
        svc = ForgotPasswordService(
            user_repo=UserRepository(db_session),
            redis_client=redis_client,
            email_service=email_svc,
            settings=settings,
        )
        await svc.execute(ForgotPasswordPayload(email="forgotpw@test.com"))
        reset_keys = [k for k in redis_client._store if k.startswith("authcore:reset:")]  # type: ignore[attr-defined]
        assert len(reset_keys) >= 1

    async def test_reset_password_with_valid_token(
        self, db_session: AsyncSession, redis_client: RedisClient
    ) -> None:
        user = await _make_user(db_session, email="resetpw@test.com")
        token = "resettoken123"
        await redis_client.set(f"authcore:reset:{token}", str(user.id))

        svc = ResetPasswordService(
            user_repo=UserRepository(db_session),
            token_repo=RefreshTokenRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
            redis_client=redis_client,
        )
        result = await svc.execute(
            ResetPasswordPayload(token=token, new_password="NewSecure3#")
        )
        assert result.reset is True
        assert result.user_id == user.id

    async def test_reset_password_invalid_token_raises(
        self, db_session: AsyncSession, redis_client: RedisClient
    ) -> None:
        svc = ResetPasswordService(
            user_repo=UserRepository(db_session),
            token_repo=RefreshTokenRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
            redis_client=redis_client,
        )
        with pytest.raises(TokenInvalidError):
            await svc.execute(ResetPasswordPayload(token="badtoken", new_password="NewSecure3#"))

    async def test_reset_password_weak_new_raises(
        self, db_session: AsyncSession, redis_client: RedisClient
    ) -> None:
        user = await _make_user(db_session, email="weakreset@test.com")
        token = "weakresettoken"
        await redis_client.set(f"authcore:reset:{token}", str(user.id))
        svc = ResetPasswordService(
            user_repo=UserRepository(db_session),
            token_repo=RefreshTokenRepository(db_session),
            audit_repo=AuditLogRepository(db_session),
            redis_client=redis_client,
        )
        with pytest.raises(PasswordWeakError):
            await svc.execute(ResetPasswordPayload(token=token, new_password="abc"))


class TestResendVerificationService:
    async def test_resend_sends_email(
        self, db_session: AsyncSession, redis_client: RedisClient, settings: Settings
    ) -> None:
        user = await _make_user(db_session, email="resend@test.com", is_verified=False)
        email_svc = AsyncMock()
        svc = ResendVerificationService(
            user_repo=UserRepository(db_session),
            redis_client=redis_client,
            email_service=email_svc,
            settings=settings,
        )
        result = await svc.execute(ResendVerificationPayload(user_id=user.id))
        assert result.sent is True

    async def test_resend_rate_limit_exceeded_raises(
        self, db_session: AsyncSession, redis_client: RedisClient, settings: Settings
    ) -> None:
        user = await _make_user(db_session, email="resendrl@test.com", is_verified=False)
        # Pre-fill resend counter beyond limit
        max_resends = settings.resend_verification_max_per_hour
        for _ in range(max_resends):
            await redis_client.incr(f"authcore:resend:{user.id}")

        email_svc = AsyncMock()
        svc = ResendVerificationService(
            user_repo=UserRepository(db_session),
            redis_client=redis_client,
            email_service=email_svc,
            settings=settings,
        )
        with pytest.raises(ResendRateLimitedError):
            await svc.execute(ResendVerificationPayload(user_id=user.id))
