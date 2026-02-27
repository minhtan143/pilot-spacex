"""Repository for audit log persistence."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from authcore.domain.models.audit_log import AuditLogEntity
from authcore.infrastructure.database.models.audit_log import AuditLogModel


def _to_entity(m: AuditLogModel) -> AuditLogEntity:
    return AuditLogEntity(
        id=m.id,
        action=m.action,
        created_at=m.created_at,
        user_id=m.user_id,
        metadata={str(k): v for k, v in (m.metadata_ or {}).items()},
        ip_address=str(m.ip_address) if m.ip_address else None,
    )


class AuditLogRepository:
    """Append-only repository for audit log entries. No updates or deletes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        user_id: uuid.UUID | None,
        action: str,
        metadata: dict[str, object],
        ip_address: str | None = None,
    ) -> AuditLogEntity:
        """Append a new audit log entry.

        Args:
            user_id: UUID of the acting user, or None for anonymous events.
            action: Machine-readable action name (e.g. 'LOGIN', 'LOGOUT').
            metadata: Arbitrary event metadata dict stored as JSONB.
            ip_address: Client IP address string, or None if unavailable.

        Returns:
            Created AuditLogEntity reflected from DB.
        """
        model = AuditLogModel(
            user_id=user_id,
            action=action,
            metadata_=metadata,
            ip_address=ip_address,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_entity(model)

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLogEntity]:
        """List audit log entries for a specific user, newest first.

        Args:
            user_id: UUID of the user to query.
            limit: Maximum number of entries to return.
            offset: Number of entries to skip for pagination.

        Returns:
            List of AuditLogEntity ordered by created_at descending.
        """
        result = await self._session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.user_id == user_id)
            .order_by(AuditLogModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [_to_entity(m) for m in result.scalars().all()]
