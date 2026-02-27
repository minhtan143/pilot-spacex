"""CQRS service: authenticate user credentials and issue JWT token pair."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import bcrypt
import structlog

from authcore.config import Settings
from authcore.domain.exceptions import (
    AccountLockedError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    LoginRateLimitedError,
)
from authcore.domain.models.refresh_token import RefreshTokenEntity
from authcore.external.rate_limiter import LoginRateLimiter
from authcore.infrastructure.database.repositories.audit_log_repository import AuditLogRepository
from authcore.infrastructure.database.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from authcore.infrastructure.database.repositories.user_repository import UserRepository
from authcore.infrastructure.tokens.jwt_service import JWTService

logger = structlog.get_logger(__name__)

# Pre-computed dummy hash for constant-time comparison when email not found
_DUMMY_HASH: bytes = bcrypt.hashpw(b"dummy-sentinel", bcrypt.gensalt(rounds=4))


@dataclass(frozen=True)
class LoginPayload:
    """Input for login."""

    email: str
    password: str
    ip_address: str = "unknown"


@dataclass(frozen=True)
class LoginResult:
    """Output of successful login."""

    access_token: str
    refresh_token: str
    token_type: str
    user_id: uuid.UUID
    role: str


class LoginService:
    """Authenticate user: check lockout, rate limit, verify bcrypt, issue RS256 JWT pair."""

    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
        audit_repo: AuditLogRepository,
        jwt_service: JWTService,
        rate_limiter: LoginRateLimiter,
        settings: Settings,
    ) -> None:
        self._user_repo = user_repo
        self._token_repo = token_repo
        self._audit_repo = audit_repo
        self._jwt = jwt_service
        self._rate_limiter = rate_limiter
        self._settings = settings

    async def execute(self, payload: LoginPayload) -> LoginResult:
        """Authenticate user and return a JWT token pair.

        Args:
            payload: Login credentials and client IP.

        Returns:
            LoginResult with access and refresh tokens.

        Raises:
            LoginRateLimitedError: If IP+email has exceeded failure threshold.
            InvalidCredentialsError: If email unknown or password wrong.
            EmailNotVerifiedError: If account email is unverified.
            AccountLockedError: If account is temporarily locked.
        """
        # 1. Check IP+email rate limit before any DB hit
        if await self._rate_limiter.is_rate_limited(payload.ip_address, payload.email):
            raise LoginRateLimitedError(
                "Too many failed login attempts. Try again later."
            )

        # 2. Load user (constant-time: always attempt bcrypt even on miss)
        user = await self._user_repo.get_by_email(payload.email)

        # 3. Constant-time password check to prevent timing attacks
        candidate_hash = (
            user.hashed_password.encode() if user is not None else _DUMMY_HASH
        )
        try:
            password_ok = bcrypt.checkpw(payload.password.encode(), candidate_hash)
        except ValueError:
            password_ok = False

        if user is None or not password_ok:
            # Record failure for existing users
            if user is not None:
                user.record_failed_attempt(
                    max_attempts=self._settings.login_max_attempts,
                    lockout_minutes=self._settings.login_lockout_minutes,
                )
                await self._user_repo.save_entity(user)
                await self._rate_limiter.record_failure(payload.ip_address, payload.email)
                await self._audit_repo.append(
                    user.id, "LOGIN_FAILED", {"reason": "bad_password"}, payload.ip_address
                )
            raise InvalidCredentialsError("Invalid email or password")

        # 4. Auto-unlock if lockout expired
        user.auto_unlock_if_expired()

        # 5. Guard: email verified
        if not user.is_verified:
            raise EmailNotVerifiedError("Please verify your email before logging in")

        # 6. Guard: account locked
        if user.is_lockout_active():
            raise AccountLockedError(
                f"Account is locked until {user.lockout_until.isoformat()}"  # type: ignore[union-attr]
            )

        # 7. Clear failed attempts on success
        user.clear_failed_attempts()
        await self._user_repo.save_entity(user)
        await self._rate_limiter.clear(payload.ip_address, payload.email)

        # 8. Issue JWT pair
        jti = uuid.uuid4()
        access_token, _ = self._jwt.create_access_token(user.id, user.role, jti)
        raw_refresh, refresh_hash = self._jwt.create_refresh_token_pair()

        family_id = uuid.uuid4()
        expires_at = datetime.now(tz=UTC) + timedelta(
            days=self._settings.refresh_token_expire_days
        )
        refresh_entity = RefreshTokenEntity(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=refresh_hash,
            family_id=family_id,
            is_revoked=False,
            expires_at=expires_at,
            created_at=datetime.now(tz=UTC),
        )
        await self._token_repo.create_token(refresh_entity)

        await self._audit_repo.append(
            user.id, "LOGIN", {"ip": payload.ip_address}, payload.ip_address
        )

        logger.info("user_logged_in", user_id=str(user.id), ip=payload.ip_address)
        return LoginResult(
            access_token=access_token,
            refresh_token=raw_refresh,
            token_type="bearer",
            user_id=user.id,
            role=user.role,
        )
