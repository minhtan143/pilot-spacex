"""Add supabase_invite_sent_at to workspace_invitations.

Tracks when Supabase inviteUserByEmail() was called for a pending invitation.
Used to prevent duplicate magic link emails on admin retry.

Revision ID: 102_workspace_invitation_supabase
Revises: 101_project_rbac_rls
Create Date: 2026-03-25
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "102_workspace_invitation_supabase"
down_revision: str | None = "101_project_rbac_rls"
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "workspace_invitations",
        sa.Column(
            "supabase_invite_sent_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Set when Supabase inviteUserByEmail() is called; prevents duplicate magic links on retry",
        ),
    )


def downgrade() -> None:
    op.drop_column("workspace_invitations", "supabase_invite_sent_at")
