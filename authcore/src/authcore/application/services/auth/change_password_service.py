"""CQRS service: change password — verify current, validate new, invalidate sessions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import bcrypt
import structlog

from authcore.domain.exceptions import PasswordMismatchError, PasswordWeakError, UserNotFoundError
from authcore.domain.services.password_policy import PasswordPolicy
from authcore.infrastructure.database.repositories.audit_log_repository import AuditLogRepository
from authcore.infrastructure.database.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from authcore.infrastructure.database.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ChangePasswordPayload:
    """Input for change-password."""

    user_id: uuid.UUID
    current_password: str
    new_password: str
    ip_address: str = "unknown"


@dataclass(frozen=True)
class ChangePasswordResult:
    """Output of change-password."""

    changed: bool


class ChangePasswordService:
    """Verify current password, enforce new password policy, rotate hash, revoke all sessions."""

    def __init__(
        self,
        user_repo: UserRepository,
        token_repo: RefreshTokenRepository,
        audit_repo: AuditLogRepository,
    ) -> None:
        self._user_repo = user_repo
        self._token_repo = token_repo
        self._audit_repo = audit_repo
        self._policy = PasswordPolicy()

    async def execute(self, payload: ChangePasswordPayload) -> ChangePasswordResult:
        """Change the user's password.

        Args:
            payload: User ID, current password, and new password.

        Returns:
            ChangePasswordResult with changed=True.

        Raises:
            UserNotFoundError: If the user does not exist.
            PasswordMismatchError: If the current password is incorrect.
            PasswordWeakError: If the new password fails policy checks.
        """
        user = await self._user_repo.get_by_id(payload.user_id)
        if user is None:
            raise UserNotFoundError("User not found")

        # 1. Verify current password
        if not bcrypt.checkpw(
            payload.current_password.encode(), user.hashed_password.encode()
        ):
            raise PasswordMismatchError("Current password is incorrect")

        # 2. Validate new password
        result = self._policy.validate(payload.new_password)
        if not result.is_valid:
            raise PasswordWeakError("; ".join(result.failures))

        # 3. Hash and persist new password
        new_hash = bcrypt.hashpw(
            payload.new_password.encode(), bcrypt.gensalt(rounds=12)
        ).decode()
        user.hashed_password = new_hash
        await self._user_repo.save_entity(user)

        # 4. Revoke all refresh tokens (force re-login everywhere)
        await self._token_repo.revoke_all_for_user(payload.user_id)

        await self._audit_repo.append(
            payload.user_id,
            "PASSWORD_CHANGED",
            {},
            payload.ip_address,
        )
        logger.info("password_changed", user_id=str(payload.user_id))
        return ChangePasswordResult(changed=True)
