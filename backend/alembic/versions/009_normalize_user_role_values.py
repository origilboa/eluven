"""Normalize users.role to lowercase enum values.

Revision ID: 009
Revises: 008
Create Date: 2026-06-02

Migration 006 inserted the platform system user with role 'app_admin' (enum value),
while SQLAlchemy previously persisted enum member names ('APP_ADMIN'). Mixed values
caused ORM loads to fail when listing users.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ROLE_NAME_TO_VALUE = (
    ("APP_ADMIN", "app_admin"),
    ("ORG_ADMIN", "org_admin"),
    ("USER", "user"),
)


def upgrade() -> None:
    for old_value, new_value in _ROLE_NAME_TO_VALUE:
        op.execute(
            sa.text(
                "UPDATE users SET role = :new_value WHERE role = :old_value"
            ).bindparams(old_value=old_value, new_value=new_value)
        )


def downgrade() -> None:
    for old_value, new_value in _ROLE_NAME_TO_VALUE:
        op.execute(
            sa.text(
                "UPDATE users SET role = :old_value WHERE role = :new_value"
            ).bindparams(old_value=old_value, new_value=new_value)
        )
