"""Add task_documents table and migrate thread documents.

Revision ID: 007
Revises: 006
Create Date: 2026-06-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)
_NOW = sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "task_documents",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("task_id", _UUID, sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("s3_key", sa.String(500), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("load_strategy", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),
        sa.Column("uploaded_by", _UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
    )
    op.create_index("ix_task_documents_task_id", "task_documents", ["task_id"])

    op.add_column(
        "document_chunks",
        sa.Column("task_document_id", _UUID, sa.ForeignKey("task_documents.id"), nullable=True),
    )
    op.create_index(
        "ix_document_chunks_task_document_id",
        "document_chunks",
        ["task_document_id"],
    )

    op.execute(
        """
        INSERT INTO task_documents (
            id, task_id, filename, s3_key, size_bytes, file_type,
            token_count, load_strategy, status, uploaded_by, created_at
        )
        SELECT
            td.id, t.task_id, td.filename, td.s3_key, td.size_bytes, td.file_type,
            td.token_count, td.load_strategy, td.status, td.uploaded_by, td.created_at
        FROM thread_documents td
        JOIN threads t ON td.thread_id = t.id
        """,
    )

    op.execute(
        """
        UPDATE document_chunks
        SET task_document_id = thread_document_id
        WHERE thread_document_id IS NOT NULL
        """,
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_task_document_id", table_name="document_chunks")
    op.drop_column("document_chunks", "task_document_id")
    op.drop_index("ix_task_documents_task_id", table_name="task_documents")
    op.drop_table("task_documents")
