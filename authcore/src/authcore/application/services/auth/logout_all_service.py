"""CQRS service: logout all sessions for a user (revoke all refresh tokens)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import structlog

from authcore.infrastructure.database.repositories.audit_log_repository import AuditLogRepository
from authcore.infrastructure.database.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class LogoutAllPayload:
    """Input for logout-all."""

    user_id: uuid.UUID
    ip_address: str = "unknown"


@dataclass(frozen=True)
class LogoutAllResult:
    """Output of logout-all."""

    revoked: bool


class LogoutAllService:
    """Revoke all active refresh tokens for the requesting user."""

    def __init__(
        self,
        token_repo: RefreshTokenRepository,
        audit_repo: AuditLogRepository,
    ) -> None:
        self._token_repo = token_repo
        self._audit_repo = audit_repo

    async def execute(self, payload: LogoutAllPayload) -> LogoutAllResult:
        """Revoke every refresh token belonging to the user.

        Note: Access tokens remain valid until they expire naturally.
        For immediate invalidation use the JTI blacklist (logout_service).

        Args:
            payload: Target user ID.

        Returns:
            LogoutAllResult indicating revocation completed.
        """
        await self._token_repo.revoke_all_for_user(payload.user_id)
        await self._audit_repo.append(
            payload.user_id,
            "LOGOUT_ALL",
            {},
            payload.ip_address,
        )
        logger.info("all_sessions_revoked", user_id=str(payload.user_id))
        return LogoutAllResult(revoked=True)
