"""CQRS service: consume email verification token and mark user as verified."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import structlog

from authcore.domain.exceptions import AlreadyVerifiedError, TokenInvalidError, UserNotFoundError
from authcore.infrastructure.cache.redis_client import RedisClient
from authcore.infrastructure.database.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)

_VERIFY_PREFIX = "authcore:verify:"


@dataclass(frozen=True)
class VerifyEmailPayload:
    """Input for email verification."""

    token: str


@dataclass(frozen=True)
class VerifyEmailResult:
    """Output of email verification."""

    user_id: uuid.UUID
    email: str


class VerifyEmailService:
    """Consume a one-time email verification token and activate the user account."""

    def __init__(
        self,
        user_repo: UserRepository,
        redis_client: RedisClient,
    ) -> None:
        self._user_repo = user_repo
        self._redis = redis_client

    async def execute(self, payload: VerifyEmailPayload) -> VerifyEmailResult:
        """Verify user email.

        Args:
            payload: Verification token from the email link.

        Returns:
            VerifyEmailResult with the now-verified user's ID and email.

        Raises:
            TokenInvalidError: If the token is unknown or expired.
            UserNotFoundError: If the user referenced by the token no longer exists.
            AlreadyVerifiedError: If the account was already verified.
        """
        key = f"{_VERIFY_PREFIX}{payload.token}"

        # 1. Look up token in Redis
        user_id_str = await self._redis.get(key)
        if user_id_str is None:
            raise TokenInvalidError("Verification token is invalid or expired")

        user_id = uuid.UUID(user_id_str)

        # 2. Load user
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError("User associated with this token no longer exists")

        # 3. Guard: already verified
        if user.is_verified:
            # Still consume the token to prevent replay
            await self._redis.delete(key)
            raise AlreadyVerifiedError("Email address is already verified")

        # 4. Mark verified + persist
        user.is_verified = True
        user = await self._user_repo.save_entity(user)

        # 5. Consume token (one-time use)
        await self._redis.delete(key)

        logger.info("email_verified", user_id=str(user_id))
        return VerifyEmailResult(user_id=user.id, email=user.email)
