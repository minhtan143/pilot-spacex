"""SQLAlchemy model for the users table."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text

from authcore.infrastructure.database.base import Base, SoftDeleteMixin, TimestampMixin


class UserModel(Base, TimestampMixin, SoftDeleteMixin):
    """Persistent user record.

    Stores credentials, role, verification state, and account lock info.
    Soft-delete via SoftDeleteMixin — user rows are never hard-deleted.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'member'"))
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    lockout_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("role IN ('admin','member','guest')", name="ck_users_role"),
        Index("ix_users_role", "role"),
        Index("ix_users_is_deleted", "is_deleted"),
    )

    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, email={self.email})>"
