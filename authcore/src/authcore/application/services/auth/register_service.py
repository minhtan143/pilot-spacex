"""CQRS service: register a new user and send email verification."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import bcrypt
import structlog

from authcore.config import Settings
from authcore.domain.exceptions import EmailExistsError, PasswordWeakError
from authcore.domain.models.user import UserEntity
from authcore.domain.services.password_policy import PasswordPolicy
from authcore.infrastructure.cache.redis_client import RedisClient
from authcore.infrastructure.database.repositories.user_repository import UserRepository
from authcore.infrastructure.email.email_service import AbstractEmailService

logger = structlog.get_logger(__name__)

_TOKEN_BYTES = 32


@dataclass(frozen=True)
class RegisterPayload:
    """Input for user registration."""

    email: str
    password: str
    ip_address: str | None = None


@dataclass(frozen=True)
class RegisterResult:
    """Output of user registration."""

    user_id: uuid.UUID
    email: str
    verification_sent: bool


class RegisterService:
    """Register a new user: validate, hash password, store, send verification email."""

    def __init__(
        self,
        user_repo: UserRepository,
        redis_client: RedisClient,
        email_service: AbstractEmailService,
        settings: Settings,
    ) -> None:
        self._user_repo = user_repo
        self._redis = redis_client
        self._email_service = email_service
        self._settings = settings
        self._policy = PasswordPolicy()

    async def execute(self, payload: RegisterPayload) -> RegisterResult:
        """Register a user.

        Args:
            payload: Registration input (email, password, optional IP).

        Returns:
            RegisterResult with new user ID and verification status.

        Raises:
            EmailExistsError: If the email is already registered.
            PasswordWeakError: If the password fails policy checks.
        """
        # 1. Check email uniqueness
        existing = await self._user_repo.get_by_email(payload.email)
        if existing is not None:
            raise EmailExistsError(f"Email already registered: {payload.email}")

        # 2. Validate password policy
        result = self._policy.validate(payload.password)
        if not result.is_valid:
            raise PasswordWeakError("; ".join(result.failures))

        # 3. Hash password
        hashed = bcrypt.hashpw(
            payload.password.encode(), bcrypt.gensalt(rounds=12)
        ).decode()

        # 4. Persist user
        entity = UserEntity(
            id=uuid.uuid4(),
            email=payload.email,
            hashed_password=hashed,
            role="member",
            is_verified=False,
            is_locked=False,
            failed_attempts=0,
            lockout_until=None,
            created_at=datetime.now(tz=UTC),
        )
        entity = await self._user_repo.save_entity(entity)

        # 5. Generate + store verification token
        raw_token = secrets.token_urlsafe(_TOKEN_BYTES)
        ttl = self._settings.email_verification_token_expire_hours * 3600
        await self._redis.set(
            f"authcore:verify:{raw_token}", str(entity.id), ex=ttl
        )

        # 6. Send verification email (non-critical — log and continue on failure)
        verification_sent = False
        try:
            await self._email_service.send_verification(
                payload.email, raw_token, self._settings.app_base_url
            )
            verification_sent = True
        except Exception:
            logger.exception(
                "register_verification_email_failed", email=payload.email
            )

        logger.info(
            "user_registered",
            user_id=str(entity.id),
            email=payload.email,
            ip=payload.ip_address,
        )
        return RegisterResult(
            user_id=entity.id,
            email=entity.email,
            verification_sent=verification_sent,
        )
