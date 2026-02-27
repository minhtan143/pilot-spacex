"""Generic base repository with CRUD and offset pagination for AuthCore.

Provides consistent data access patterns for all entities.
No workspace scoping — AuthCore is not multi-tenant.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, TypeVar
from uuid import UUID

from sqlalchemy import ColumnElement, and_, func, select

from authcore.infrastructure.database.base import BaseModel

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T", bound=BaseModel)


class BaseRepository[T: BaseModel]:
    """Generic repository with CRUD and soft delete support.

    Provides consistent data access patterns for all entities.
    Uses soft delete by default — entities are marked as deleted rather than removed.

    Type Parameters:
        T: The SQLAlchemy model type.

    Attributes:
        session: The async database session.
        model_class: The SQLAlchemy model class.
    """

    def __init__(self, session: AsyncSession, model_class: type[T]) -> None:
        """Initialize repository with session and model class.

        Args:
            session: The async database session.
            model_class: The SQLAlchemy model class.
        """
        self.session = session
        self.model_class = model_class

    async def get_by_id(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> T | None:
        """Get entity by ID.

        Args:
            entity_id: The entity UUID.
            include_deleted: Whether to include soft-deleted entities.

        Returns:
            The entity if found, None otherwise.
        """
        query = select(self.model_class).where(self.model_class.id == entity_id)
        if not include_deleted:
            query = query.where(self.model_class.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, entity: T) -> T:
        """Create a new entity.

        Args:
            entity: The entity to create.

        Returns:
            The created entity with generated ID and timestamps.
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity: T) -> T:
        """Flush pending changes and refresh entity from DB.

        Args:
            entity: The entity to update.

        Returns:
            The updated entity.
        """
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: T, *, hard: bool = False) -> None:
        """Delete an entity (soft delete by default).

        Args:
            entity: The entity to delete.
            hard: If True, permanently delete. If False, soft delete.
        """
        if hard:
            await self.session.delete(entity)
        else:
            entity.is_deleted = True  # type: ignore[attr-defined]
            entity.deleted_at = datetime.now(tz=UTC)  # type: ignore[attr-defined]
        await self.session.flush()

    async def list(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> Sequence[T]:
        """List entities with offset-based pagination.

        Args:
            limit: Maximum number of entities to return (capped at 100).
            offset: Number of entities to skip.
            include_deleted: Whether to include soft-deleted entities.

        Returns:
            List of entities ordered by created_at descending.
        """
        limit = min(limit, 100)
        query = select(self.model_class)
        if not include_deleted:
            query = query.where(self.model_class.is_deleted == False)  # noqa: E712
        query = query.order_by(self.model_class.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count(self, *, include_deleted: bool = False) -> int:
        """Count all entities.

        Args:
            include_deleted: Whether to include soft-deleted entities.

        Returns:
            Count of matching entities.
        """
        query = select(func.count()).select_from(self.model_class)
        if not include_deleted:
            query = query.where(self.model_class.is_deleted == False)  # noqa: E712
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def find_one_by(
        self,
        *,
        include_deleted: bool = False,
        **kwargs: Any,
    ) -> T | None:
        """Find single entity by attribute values.

        Args:
            include_deleted: Whether to include soft-deleted entities.
            **kwargs: Column=value pairs to filter by.

        Returns:
            The entity if found, None otherwise.
        """
        query = select(self.model_class)
        if not include_deleted:
            query = query.where(self.model_class.is_deleted == False)  # noqa: E712
        conditions: list[ColumnElement[bool]] = []
        for key, value in kwargs.items():
            if hasattr(self.model_class, key):
                column = getattr(self.model_class, key)
                conditions.append(column == value)  # type: ignore[arg-type]
        if conditions:
            query = query.where(and_(*conditions))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
