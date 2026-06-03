"""Normalize VARCHAR enum columns from member names to lowercase values.

Revision ID: 011
Revises: 010
Create Date: 2026-06-02

Earlier ORM versions persisted Enum member names (e.g. DRAFT) while values_callable
now expects stored values (draft). Migration 009 fixed users.role only.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, column) — lower() maps NAME -> value for all platform enums.
_ENUM_COLUMNS = (
    ("tasks", "status"),
    ("threads", "status"),
    ("thread_messages", "role"),
    ("task_memory_entries", "entry_type"),
    ("workflow_executions", "status"),
    ("workflow_thread_executions", "status"),
    ("workflow_interventions", "trigger_type"),
    ("kb_documents", "status"),
    ("task_documents", "status"),
    ("task_documents", "load_strategy"),
    ("thread_documents", "status"),
    ("thread_documents", "load_strategy"),
    ("instruction_sets", "level"),
    ("thread_qa_questions", "stage"),
    ("thread_qa_questions", "response_type"),
    ("users", "role"),
    ("user_invitations", "role"),
)


def _normalize_column(table: str, column: str) -> None:
    op.execute(
        sa.text(
            f'UPDATE "{table}" SET "{column}" = lower("{column}") '
            f'WHERE "{column}" != lower("{column}")'
        )
    )


def upgrade() -> None:
    for table, column in _ENUM_COLUMNS:
        _normalize_column(table, column)


def downgrade() -> None:
    pass
