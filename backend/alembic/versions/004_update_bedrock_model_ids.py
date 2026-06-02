"""Update ActivityLibrary Bedrock model IDs after Claude 3.5 EOL.

Revision ID: 004
Revises: 003
Create Date: 2026-06-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_DEFAULT_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
OLD_HAIKU_MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"
NEW_DEFAULT_MODEL_ID = "anthropic.claude-sonnet-4-5-20250929-v1:0"
NEW_HAIKU_MODEL_ID = "anthropic.claude-haiku-4-5-20251001-v1:0"

_ACTIVITY_LIBRARY = sa.table(
    "activity_library_entries",
    sa.column("default_model_id", sa.String),
    sa.column("fallback_model_id", sa.String),
)


def upgrade() -> None:
    op.execute(
        _ACTIVITY_LIBRARY.update()
        .where(_ACTIVITY_LIBRARY.c.default_model_id == OLD_DEFAULT_MODEL_ID)
        .values(default_model_id=NEW_DEFAULT_MODEL_ID)
    )
    op.execute(
        _ACTIVITY_LIBRARY.update()
        .where(_ACTIVITY_LIBRARY.c.fallback_model_id == OLD_HAIKU_MODEL_ID)
        .values(fallback_model_id=NEW_HAIKU_MODEL_ID)
    )
    op.execute(
        _ACTIVITY_LIBRARY.update()
        .where(_ACTIVITY_LIBRARY.c.fallback_model_id == OLD_DEFAULT_MODEL_ID)
        .values(fallback_model_id=NEW_DEFAULT_MODEL_ID)
    )


def downgrade() -> None:
    op.execute(
        _ACTIVITY_LIBRARY.update()
        .where(_ACTIVITY_LIBRARY.c.default_model_id == NEW_DEFAULT_MODEL_ID)
        .values(default_model_id=OLD_DEFAULT_MODEL_ID)
    )
    op.execute(
        _ACTIVITY_LIBRARY.update()
        .where(_ACTIVITY_LIBRARY.c.fallback_model_id == NEW_HAIKU_MODEL_ID)
        .values(fallback_model_id=OLD_HAIKU_MODEL_ID)
    )
    op.execute(
        _ACTIVITY_LIBRARY.update()
        .where(_ACTIVITY_LIBRARY.c.fallback_model_id == NEW_DEFAULT_MODEL_ID)
        .values(fallback_model_id=OLD_DEFAULT_MODEL_ID)
    )
