"""SQLAlchemy model for the refresh_tokens table."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from authcore.infrastructure.database.base import Base


class RefreshTokenModel(Base):
    """Persistent refresh token with family tracking for theft detection.

    Tokens are grouped by family_id. When a revoked token is reused, the
    entire family is revoked (token rotation / theft detection).
    Tokens are never soft-deleted — expired rows are purged by a scheduled job.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    family_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_family_id", "family_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<RefreshTokenModel(id={self.id}, user_id={self.user_id})>"
