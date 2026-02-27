"""CQRS service: consume password reset token and set new password."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import bcrypt
import structlog

from authcore.domain.exceptions import PasswordWeakError, TokenInvalidError, UserNotFoundError
from authcore.domain.services.password_policy import PasswordPolicy
from authcore.infrastructure.cache.redis_client import RedisClient
from authcore.infrastructure.database.repositories.audit_log_repository import AuditLogRepository
from authcore.infrastructure.database.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from authcore.infrastructure.database.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)

_RESET_PREFIX = "authcore:reset:"


@dataclass(frozen=True)
class ResetPasswordPayload:
    """Input for password reset."""

    token: str
    new_password: str
    ip_address: str = "unknown"


@dataclass(frozen=True)
class ResetPasswordResult:
    """Output of password reset."""

    reset: bool
    user_id: uuid.UUID


class ResetPasswordService:
    """Consume a password reset token, set new password, revoke all sessions."""

    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
        audit_repo: AuditLogRepository,
        redis_client: RedisClient,
    ) -> None:
        self._user_repo = user_repo
        self._token_repo = token_repo
        self._audit_repo = audit_repo
        self._redis = redis_client
        self._policy = PasswordPolicy()

    async def execute(self, payload: ResetPasswordPayload) -> ResetPasswordResult:
        """Reset password using a one-time token.

        Args:
            payload: Reset token, new password, and client IP.

        Returns:
            ResetPasswordResult indicating success.

        Raises:
            TokenInvalidError: If the reset token is unknown or expired.
            UserNotFoundError: If the associated user no longer exists.
            PasswordWeakError: If the new password fails policy checks.
        """
        key = f"{_RESET_PREFIX}{payload.token}"

        # 1. Look up token
        user_id_str = await self._redis.get(key)
        if user_id_str is None:
            raise TokenInvalidError("Password reset token is invalid or expired")

        user_id = uuid.UUID(user_id_str)

        # 2. Load user
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError("User associated with this reset token no longer exists")

        # 3. Validate new password
        result = self._policy.validate(payload.new_password)
        if not result.is_valid:
            raise PasswordWeakError("; ".join(result.failures))

        # 4. Hash and persist new password
        new_hash = bcrypt.hashpw(
            payload.new_password.encode(), bcrypt.gensalt(rounds=12)
        ).decode()
        user.hashed_password = new_hash
        # Reset verification state for locked accounts
        user.clear_failed_attempts()
        await self._user_repo.save_entity(user)

        # 5. Consume token (one-time use)
        await self._redis.delete(key)

        # 6. Revoke all refresh tokens
        await self._token_repo.revoke_all_for_user(user_id)

        await self._audit_repo.append(
            user_id,
            "PASSWORD_RESET",
            {},
            payload.ip_address,
        )
        logger.info("password_reset", user_id=str(user_id))
        return ResetPasswordResult(reset=True, user_id=user_id)
