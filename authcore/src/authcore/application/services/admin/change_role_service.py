"""CQRS service: admin — change a user's role."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import structlog

from authcore.domain.exceptions import AuthForbiddenError, InvalidRoleError, UserNotFoundError
from authcore.infrastructure.database.repositories.audit_log_repository import AuditLogRepository
from authcore.infrastructure.database.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)

_VALID_ROLES = frozenset({"admin", "member", "guest"})


@dataclass(frozen=True)
class ChangeRolePayload:
    """Input for admin role change."""

    admin_user_id: uuid.UUID
    target_user_id: uuid.UUID
    new_role: str
    ip_address: str = "unknown"


@dataclass(frozen=True)
class ChangeRoleResult:
    """Output of admin role change."""

    user_id: uuid.UUID
    new_role: str


class ChangeRoleService:
    """Admin operation: change target user's role with audit logging."""

    def __init__(
        self,
        user_repo: UserRepository,
        audit_repo: AuditLogRepository,
    ) -> None:
        self._user_repo = user_repo
        self._audit_repo = audit_repo

    async def execute(self, payload: ChangeRolePayload) -> ChangeRoleResult:
        """Change a user's role.

        Args:
            payload: Admin user ID, target user ID, and new role.

        Returns:
            ChangeRoleResult with updated user ID and role.

        Raises:
            AuthForbiddenError: If the acting user is not an admin.
            UserNotFoundError: If either user does not exist.
            InvalidRoleError: If the new role is not one of admin/member/guest.
        """
        # 1. Verify admin role
        admin = await self._user_repo.get_by_id(payload.admin_user_id)
        if admin is None:
            raise UserNotFoundError("Admin user not found")
        if admin.role != "admin":
            raise AuthForbiddenError("Only admins can change user roles")

        # 2. Validate new role
        if payload.new_role not in _VALID_ROLES:
            raise InvalidRoleError(
                f"Invalid role '{payload.new_role}'. Must be one of: {', '.join(sorted(_VALID_ROLES))}"
            )

        # 3. Load target user
        target = await self._user_repo.get_by_id(payload.target_user_id)
        if target is None:
            raise UserNotFoundError("Target user not found")

        previous_role = target.role

        # 4. Update role
        target.role = payload.new_role
        target = await self._user_repo.save_entity(target)

        await self._audit_repo.append(
            payload.admin_user_id,
            "ROLE_CHANGED",
            {
                "target_user_id": str(payload.target_user_id),
                "from": previous_role,
                "to": payload.new_role,
            },
            payload.ip_address,
        )

        logger.info(
            "role_changed",
            admin_id=str(payload.admin_user_id),
            target_id=str(payload.target_user_id),
            from_role=previous_role,
            to_role=payload.new_role,
        )
        return ChangeRoleResult(user_id=target.id, new_role=target.role)
