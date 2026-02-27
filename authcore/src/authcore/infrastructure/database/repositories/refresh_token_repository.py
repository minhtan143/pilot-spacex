"""Repository for refresh token persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from authcore.domain.models.refresh_token import RefreshTokenEntity
from authcore.infrastructure.database.models.refresh_token import RefreshTokenModel


def _utc(dt: datetime) -> datetime:
    """Ensure datetime is UTC-aware (SQLite returns naive datetimes)."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _to_entity(m: RefreshTokenModel) -> RefreshTokenEntity:
    return RefreshTokenEntity(
        id=m.id,
        user_id=m.user_id,
        token_hash=m.token_hash,
        family_id=m.family_id,
        is_revoked=m.is_revoked,
        expires_at=_utc(m.expires_at),
        created_at=_utc(m.created_at),
    )


class RefreshTokenRepository:
    """Repository for RefreshTokenModel.

    Not a soft-delete repository — expired rows are purged by a scheduled job.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_hash(self, token_hash: str) -> RefreshTokenEntity | None:
        """Find a refresh token by its SHA-256 hash.

        Args:
            token_hash: SHA-256 hex digest of the raw token.

        Returns:
            RefreshTokenEntity if found, None otherwise.
        """
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        model = result.scalar_one_or_none()
        return _to_entity(model) if model else None

    async def create_token(self, entity: RefreshTokenEntity) -> RefreshTokenEntity:
        """Persist a new refresh token.

        Args:
            entity: RefreshTokenEntity to insert.

        Returns:
            Persisted entity reflected from DB.
        """
        model = RefreshTokenModel(
            id=entity.id,
            user_id=entity.user_id,
            token_hash=entity.token_hash,
            family_id=entity.family_id,
            is_revoked=entity.is_revoked,
            expires_at=entity.expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        return _to_entity(model)

    async def revoke_by_id(self, token_id: uuid.UUID) -> None:
        """Mark a single token as revoked.

        Args:
            token_id: UUID of the token to revoke.
        """
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.id == token_id)
            .values(is_revoked=True)
        )

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        """Revoke all tokens in a token family (theft detection).

        Args:
            family_id: UUID of the token family to invalidate.
        """
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.family_id == family_id)
            .values(is_revoked=True)
        )

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Revoke all refresh tokens belonging to a user (logout-all).

        Args:
            user_id: UUID of the user whose tokens to revoke.
        """
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id)
            .values(is_revoked=True)
        )
