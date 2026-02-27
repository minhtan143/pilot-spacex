"""CQRS service: resend email verification link (rate-limited to 3 per hour)."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass

import structlog

from authcore.config import Settings
from authcore.domain.exceptions import (
    AlreadyVerifiedError,
    ResendRateLimitedError,
    UserNotFoundError,
)
from authcore.infrastructure.cache.redis_client import RedisClient
from authcore.infrastructure.database.repositories.user_repository import UserRepository
from authcore.infrastructure.email.email_service import AbstractEmailService

logger = structlog.get_logger(__name__)

_RESEND_PREFIX = "authcore:resend:"
_VERIFY_PREFIX = "authcore:verify:"
_RESEND_WINDOW = 3600  # 1 hour
_TOKEN_BYTES = 32


@dataclass(frozen=True)
class ResendVerificationPayload:
    """Input for resend verification request."""

    user_id: uuid.UUID


@dataclass(frozen=True)
class ResendVerificationResult:
    """Output of resend verification."""

    sent: bool


class ResendVerificationService:
    """Resend email verification link with rate limiting (max 3/hour per user)."""

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

    async def execute(self, payload: ResendVerificationPayload) -> ResendVerificationResult:
        """Resend verification email.

        Args:
            payload: Target user's UUID.

        Returns:
            ResendVerificationResult indicating whether the email was sent.

        Raises:
            UserNotFoundError: If the user does not exist.
            AlreadyVerifiedError: If the account is already verified.
            ResendRateLimitedError: If the resend limit (3/hr) is exceeded.
        """
        user = await self._user_repo.get_by_id(payload.user_id)
        if user is None:
            raise UserNotFoundError("User not found")

        if user.is_verified:
            raise AlreadyVerifiedError("Email address is already verified")

        # Rate limit: max N resends per hour
        rate_key = f"{_RESEND_PREFIX}{payload.user_id}"
        count_str = await self._redis.get(rate_key)
        current_count = int(count_str) if count_str else 0
        max_resends = self._settings.resend_verification_max_per_hour

        if current_count >= max_resends:
            raise ResendRateLimitedError(
                f"Maximum {max_resends} resends per hour exceeded"
            )

        # Increment resend counter
        new_count = await self._redis.incr(rate_key)
        if new_count == 1:
            await self._redis.expire(rate_key, _RESEND_WINDOW)

        # Issue new verification token
        raw_token = secrets.token_urlsafe(_TOKEN_BYTES)
        ttl = self._settings.email_verification_token_expire_hours * 3600
        await self._redis.set(
            f"{_VERIFY_PREFIX}{raw_token}", str(user.id), ex=ttl
        )

        sent = False
        try:
            await self._email_service.send_verification(
                user.email, raw_token, self._settings.app_base_url
            )
            sent = True
        except Exception:
            logger.exception("resend_verification_email_failed", user_id=str(user.id))

        logger.info("verification_resent", user_id=str(user.id), count=new_count)
        return ResendVerificationResult(sent=sent)
