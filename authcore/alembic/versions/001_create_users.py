"""create users table

Revision ID: 001
Revises:
Create Date: 2026-02-27 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default=sa.text("'member'")),
        sa.Column(
            "is_verified", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "is_locked", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "failed_attempts", sa.Integer, nullable=False, server_default=sa.text("0")
        ),
        sa.Column("lockout_until", sa.DateTime(timezone=True), nullable=True),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        # SoftDeleteMixin
        sa.Column(
            "is_deleted",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("role IN ('admin','member','guest')", name="ck_users_role"),
    )

    # Unique constraint on email
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    # Indexes
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_is_deleted", "users", ["is_deleted"])


def downgrade() -> None:
    op.drop_index("ix_users_is_deleted", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_table("users")
