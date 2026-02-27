"""CQRS service: logout current session (revoke refresh token + blacklist JTI)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import structlog

from authcore.config import Settings
from authcore.infrastructure.cache.redis_client import RedisClient
from authcore.infrastructure.database.repositories.audit_log_repository import AuditLogRepository
from authcore.infrastructure.database.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from authcore.infrastructure.tokens.jwt_service import JWTService

logger = structlog.get_logger(__name__)

_JTI_PREFIX = "authcore:jti_blacklist:"


@dataclass(frozen=True)
class LogoutPayload:
    """Input for logout."""

    raw_refresh_token: str
    jti: str  # JTI from the access token claims
    user_id: uuid.UUID
    ip_address: str = "unknown"


@dataclass(frozen=True)
class LogoutResult:
    """Output of logout (always succeeds if called with valid token)."""

    logged_out: bool


class LogoutService:
    """Revoke the current refresh token and blacklist the JTI in Redis."""

    def __init__(
        self,
        token_repo: RefreshTokenRepository,
        audit_repo: AuditLogRepository,
        redis_client: RedisClient,
        settings: Settings,
    ) -> None:
        self._token_repo = token_repo
        self._audit_repo = audit_repo
        self._redis = redis_client
        self._settings = settings

    async def execute(self, payload: LogoutPayload) -> LogoutResult:
        """Logout current session.

        Args:
            payload: Refresh token to revoke and JTI to blacklist.

        Returns:
            LogoutResult always with logged_out=True (idempotent).

        Raises:
            TokenInvalidError: If the refresh token hash cannot be found.
        """
        # 1. Revoke refresh token
        token_hash = JWTService.hash_token(payload.raw_refresh_token)
        stored = await self._token_repo.get_by_hash(token_hash)
        if stored is not None:
            await self._token_repo.revoke_by_id(stored.id)

        # 2. Blacklist access token JTI in Redis until it would naturally expire
        jti_key = f"{_JTI_PREFIX}{payload.jti}"
        ttl = self._settings.access_token_expire_minutes * 60
        await self._redis.set(jti_key, "1", ex=ttl)

        await self._audit_repo.append(
            payload.user_id,
            "LOGOUT",
            {"jti": payload.jti},
            payload.ip_address,
        )

        logger.info("user_logged_out", user_id=str(payload.user_id), jti=payload.jti)
        return LogoutResult(logged_out=True)
