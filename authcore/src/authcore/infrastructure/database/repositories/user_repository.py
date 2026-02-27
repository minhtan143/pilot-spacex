"""Repository for user persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from authcore.domain.models.user import UserEntity
from authcore.infrastructure.database.models.user import UserModel


def _utc(dt: datetime | None) -> datetime | None:
    """Ensure datetime is UTC-aware (SQLite returns naive datetimes)."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _to_entity(m: UserModel) -> UserEntity:
    return UserEntity(
        id=m.id,
        email=m.email,
        hashed_password=m.hashed_password,
        role=m.role,
        is_verified=m.is_verified,
        is_locked=m.is_locked,
        failed_attempts=m.failed_attempts,
        lockout_until=_utc(m.lockout_until),
        created_at=_utc(m.created_at) or datetime.now(tz=UTC),
        is_deleted=m.is_deleted,
        deleted_at=_utc(m.deleted_at),
    )


class UserRepository:
    """Repository for UserModel with entity mapping."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self, user_id: uuid.UUID, *, include_deleted: bool = False
    ) -> UserEntity | None:
        """Find user by UUID.

        Args:
            user_id: UUID of the user.
            include_deleted: Whether to include soft-deleted users.

        Returns:
            UserEntity if found, None otherwise.
        """
        query = select(UserModel).where(UserModel.id == user_id)
        if not include_deleted:
            query = query.where(UserModel.is_deleted.is_(False))
        result = await self._session.execute(query)
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def get_by_email(self, email: str) -> UserEntity | None:
        """Find active (non-deleted) user by email.

        Args:
            email: Email address to look up.

        Returns:
            UserEntity if found, None otherwise.
        """
        result = await self._session.execute(
            select(UserModel).where(
                UserModel.email == email,
                UserModel.is_deleted.is_(False),
            )
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def save_entity(self, entity: UserEntity) -> UserEntity:
        """Upsert a UserEntity: insert if new, update mutable fields if existing.

        Args:
            entity: UserEntity to persist.

        Returns:
            Persisted UserEntity reflected from DB.
        """
        result = await self._session.execute(
            select(UserModel)
            .where(UserModel.id == entity.id)
        )
        model: UserModel | None = result.scalar_one_or_none()
        if model is None:
            model = UserModel(
                id=entity.id,
                email=entity.email,
                hashed_password=entity.hashed_password,
                role=entity.role,
                is_verified=entity.is_verified,
                is_locked=entity.is_locked,
                failed_attempts=entity.failed_attempts,
                lockout_until=entity.lockout_until,
            )
            self._session.add(model)
        else:
            model.hashed_password = entity.hashed_password
            model.role = entity.role
            model.is_verified = entity.is_verified
            model.is_locked = entity.is_locked
            model.failed_attempts = entity.failed_attempts
            model.lockout_until = entity.lockout_until
            model.is_deleted = entity.is_deleted
            model.deleted_at = entity.deleted_at
            model.updated_at = datetime.now(tz=UTC)
        await self._session.flush()
        return _to_entity(model)
