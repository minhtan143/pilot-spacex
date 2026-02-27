"""CQRS service: admin — list paginated audit logs for a user."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import structlog

from authcore.domain.exceptions import AuthForbiddenError, UserNotFoundError
from authcore.domain.models.audit_log import AuditLogEntity
from authcore.infrastructure.database.repositories.audit_log_repository import AuditLogRepository
from authcore.infrastructure.database.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)

_MAX_LIMIT = 100


@dataclass(frozen=True)
class ListAuditLogsPayload:
    """Input for listing audit logs."""

    admin_user_id: uuid.UUID
    target_user_id: uuid.UUID
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class ListAuditLogsResult:
    """Output of audit log list."""

    logs: list[AuditLogEntity]
    total_returned: int


class ListAuditLogsService:
    """Admin operation: paginated audit log read for a target user."""

    def __init__(
        self,
        user_repo: UserRepository,
        audit_repo: AuditLogRepository,
    ) -> None:
        self._user_repo = user_repo
        self._audit_repo = audit_repo

    async def execute(self, payload: ListAuditLogsPayload) -> ListAuditLogsResult:
        """List audit log entries for a target user.

        Args:
            payload: Admin user ID, target user ID, and pagination params.

        Returns:
            ListAuditLogsResult with log entries and count.

        Raises:
            AuthForbiddenError: If the acting user is not an admin.
            UserNotFoundError: If the admin does not exist.
        """
        # 1. Verify admin role
        admin = await self._user_repo.get_by_id(payload.admin_user_id)
        if admin is None:
            raise UserNotFoundError("Admin user not found")
        if admin.role != "admin":
            raise AuthForbiddenError("Only admins can view audit logs")

        # 2. Clamp limit
        limit = min(payload.limit, _MAX_LIMIT)

        # 3. Query logs
        logs = await self._audit_repo.list_for_user(
            payload.target_user_id, limit=limit, offset=payload.offset
        )

        logger.info(
            "audit_logs_listed",
            admin_id=str(payload.admin_user_id),
            target_id=str(payload.target_user_id),
            count=len(logs),
        )
        return ListAuditLogsResult(logs=logs, total_returned=len(logs))
