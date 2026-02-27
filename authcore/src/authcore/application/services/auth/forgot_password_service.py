"""CQRS service: initiate password reset (silent — no email enumeration)."""

from __future__ import annotations

import secrets
from dataclasses import dataclass

import structlog

from authcore.config import Settings
from authcore.infrastructure.cache.redis_client import RedisClient
from authcore.infrastructure.database.repositories.user_repository import UserRepository
from authcore.infrastructure.email.email_service import AbstractEmailService

logger = structlog.get_logger(__name__)

_RESET_PREFIX = "authcore:reset:"
_TOKEN_BYTES = 32


@dataclass(frozen=True)
class ForgotPasswordPayload:
    """Input for forgot-password."""

    email: str
    ip_address: str = "unknown"


@dataclass(frozen=True)
class ForgotPasswordResult:
    """Output of forgot-password (always appears successful to caller)."""

    accepted: bool


class ForgotPasswordService:
    """Initiate password reset. Always returns success to prevent email enumeration."""

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

    async def execute(self, payload: ForgotPasswordPayload) -> ForgotPasswordResult:
        """Request password reset.

        Silently no-ops if email is not registered (prevents enumeration).

        Args:
            payload: Email to send reset link to and client IP.

        Returns:
            ForgotPasswordResult always with accepted=True.
        """
        user = await self._user_repo.get_by_email(payload.email)

        if user is not None:
            raw_token = secrets.token_urlsafe(_TOKEN_BYTES)
            ttl = self._settings.password_reset_token_expire_minutes * 60
            await self._redis.set(
                f"{_RESET_PREFIX}{raw_token}", str(user.id), ex=ttl
            )
            try:
                await self._email_service.send_password_reset(
                    payload.email, raw_token, self._settings.app_base_url
                )
            except Exception:
                logger.exception(
                    "forgot_password_email_failed", email=payload.email
                )

        # Always log + return accepted to prevent enumeration
        logger.info(
            "forgot_password_requested",
            found=user is not None,
            ip=payload.ip_address,
        )
        return ForgotPasswordResult(accepted=True)
