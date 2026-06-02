"""Add user_invitations table for admin invite flow.

Revision ID: 008
Revises: 007
Create Date: 2026-06-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "user_invitations",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("org_id", _UUID, sa.ForeignKey("orgs.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("app_admin", "org_admin", "user", name="userrole", native_enum=False),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("invited_by", _UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_user_invitations_token_hash"),
    )
    op.create_index("ix_user_invitations_org_id", "user_invitations", ["org_id"])
    op.create_index("ix_user_invitations_email", "user_invitations", ["email"])


def downgrade() -> None:
    op.drop_index("ix_user_invitations_email", table_name="user_invitations")
    op.drop_index("ix_user_invitations_org_id", table_name="user_invitations")
    op.drop_table("user_invitations")
