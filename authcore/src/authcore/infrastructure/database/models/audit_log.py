"""SQLAlchemy model for the audit_logs table."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from authcore.infrastructure.database.base import Base


class AuditLogModel(Base):
    """Immutable audit log record.

    Append-only. Never updated or deleted.
    Captures auth events: login, logout, registration, password change, etc.

    Note: ORM uses generic types (JSON, Uuid, String) for cross-dialect compatibility.
    Alembic migrations use PostgreSQL-specific types (JSONB, INET, UUID) for production.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column(  # type: ignore[type-arg]
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<AuditLogModel(id={self.id}, action={self.action})>"
