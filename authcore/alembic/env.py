"""Alembic environment configuration for AuthCore.

Supports async SQLAlchemy engine. Database URL is read from the
DATABASE_URL environment variable (overrides alembic.ini).
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Import all models so Alembic can detect them for autogenerate
from authcore.infrastructure.database.base import Base
from authcore.infrastructure.database.models.audit_log import AuditLogModel  # noqa: F401
from authcore.infrastructure.database.models.refresh_token import RefreshTokenModel  # noqa: F401
from authcore.infrastructure.database.models.user import UserModel  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Allow DATABASE_URL env var to override alembic.ini
_db_url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in offline mode (no live DB connection required).

    Generates SQL script output instead of executing against a live database.
    """
    context.configure(
        url=_db_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in online mode against a live database connection."""
    connectable = create_async_engine(
        _db_url or "",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


def _do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
