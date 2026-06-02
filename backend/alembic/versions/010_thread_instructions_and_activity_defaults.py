"""Activity default instructions and per-thread instruction layer.

Revision ID: 010
Revises: 009
Create Date: 2026-06-02
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "activity_library_entries",
        sa.Column("default_instruction_content", sa.Text(), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE activity_library_entries AS e
            SET default_instruction_content = iv.content
            FROM instruction_sets AS s
            INNER JOIN instruction_versions AS iv ON iv.id = s.active_version_id
            WHERE s.level = 'platform'
              AND s.thread_type IS NOT NULL
              AND s.thread_type = e.thread_type
            """,
        ),
    )

    op.add_column(
        "instruction_sets",
        sa.Column(
            "thread_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("threads.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_instruction_sets_thread_id", "instruction_sets", ["thread_id"])

    conn = op.get_bind()
    threads = conn.execute(
        sa.text(
            """
            SELECT t.id, t.org_id, t.task_id, t.thread_type, t.owner_id, task.module_type
            FROM threads AS t
            INNER JOIN tasks AS task ON task.id = t.task_id
            """,
        ),
    ).fetchall()

    for row in threads:
        thread_id = row.id
        existing = conn.execute(
            sa.text(
                "SELECT id FROM instruction_sets WHERE level = 'thread' AND thread_id = :tid",
            ),
            {"tid": thread_id},
        ).fetchone()
        if existing is not None:
            continue

        content_row = conn.execute(
            sa.text(
                """
                SELECT COALESCE(
                    NULLIF(TRIM(ttti.content), ''),
                    NULLIF(TRIM(ale.default_instruction_content), ''),
                    ''
                ) AS content
                FROM threads AS t
                INNER JOIN tasks AS task ON task.id = t.task_id
                LEFT JOIN task_thread_type_instructions AS ttti
                    ON ttti.task_id = t.task_id AND ttti.thread_type = t.thread_type
                LEFT JOIN activity_library_entries AS ale
                    ON ale.thread_type = t.thread_type
                    AND ale.module_type = task.module_type
                    AND ale.is_active = true
                WHERE t.id = :tid
                LIMIT 1
                """,
            ),
            {"tid": thread_id},
        ).fetchone()
        content = content_row.content if content_row else ""

        set_id = uuid4()
        version_id = uuid4()
        conn.execute(
            sa.text(
                """
                INSERT INTO instruction_sets (
                    id, org_id, level, thread_id, active_version_id, created_at, updated_at
                )
                VALUES (
                    :set_id, :org_id, 'thread', :thread_id, :version_id, now(), now()
                )
                """,
            ),
            {
                "set_id": set_id,
                "org_id": row.org_id,
                "thread_id": thread_id,
                "version_id": version_id,
            },
        )
        conn.execute(
            sa.text(
                """
                INSERT INTO instruction_versions (
                    id, instruction_set_id, version_number, content, change_note, created_by, created_at
                )
                VALUES (
                    :version_id, :set_id, 1, :content, 'Migration 010 backfill', :created_by, now()
                )
                """,
            ),
            {
                "version_id": version_id,
                "set_id": set_id,
                "content": content,
                "created_by": row.owner_id,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM instruction_versions WHERE change_note = 'Migration 010 backfill'"))
    conn.execute(sa.text("DELETE FROM instruction_sets WHERE level = 'thread'"))

    op.drop_index("ix_instruction_sets_thread_id", table_name="instruction_sets")
    op.drop_column("instruction_sets", "thread_id")
    op.drop_column("activity_library_entries", "default_instruction_content")
