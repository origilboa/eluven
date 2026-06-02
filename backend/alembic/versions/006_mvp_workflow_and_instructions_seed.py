"""Seed workflow templates, platform system user, and EPR platform instructions.

Revision ID: 006
Revises: 005
Create Date: 2026-06-01
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLATFORM_ORG_ID = "00000000-0000-0000-0000-000000000001"
PLATFORM_USER_ID = "00000000-0000-0000-0000-000000000002"
# bcrypt hash for unusable password — system user never logs in
SYSTEM_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewYBGUa5bP0.S5K."

TEMPLATE_EPR_FULL = "02000001-0001-4001-8001-000000000001"
TEMPLATE_SPR_FULL = "02000002-0001-4001-8001-000000000001"

INSTRUCTION_SET_INITIAL_READ = "03000001-0001-4001-8001-000000000001"
INSTRUCTION_VERSION_INITIAL_READ = "03000011-0001-4001-8001-000000000001"
INSTRUCTION_SET_FINAL = "03000002-0001-4001-8001-000000000001"
INSTRUCTION_VERSION_FINAL = "03000012-0001-4001-8001-000000000001"

_WORKFLOW_TEMPLATES = sa.table(
    "workflow_templates",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("org_id", postgresql.UUID(as_uuid=True)),
    sa.column("owner_id", postgresql.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("description", sa.Text),
    sa.column("module_type", sa.String),
    sa.column("scope", sa.String),
    sa.column("thread_sequence", postgresql.ARRAY(sa.String())),
)

_INSTRUCTION_SETS = sa.table(
    "instruction_sets",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("org_id", postgresql.UUID(as_uuid=True)),
    sa.column("level", sa.String),
    sa.column("thread_type", sa.String),
    sa.column("active_version_id", postgresql.UUID(as_uuid=True)),
)

_INSTRUCTION_VERSIONS = sa.table(
    "instruction_versions",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("instruction_set_id", postgresql.UUID(as_uuid=True)),
    sa.column("version_number", sa.Integer),
    sa.column("content", sa.Text),
    sa.column("change_note", sa.String),
    sa.column("created_by", postgresql.UUID(as_uuid=True)),
)


def upgrade() -> None:
    conn = op.get_bind()

    existing_user = conn.execute(
        sa.text("SELECT id FROM users WHERE id = :id"),
        {"id": PLATFORM_USER_ID},
    ).fetchone()
    if existing_user is None:
        op.execute(
            sa.text(
                """
                INSERT INTO users (
                    id, org_id, email, name, role, hashed_password,
                    default_working_language, is_active, created_at, updated_at
                )
                VALUES (
                    :id, :org_id, 'system@eluven.ai', 'Platform System', 'app_admin',
                    :password, 'en', true, now(), now()
                )
                """
            ).bindparams(
                id=UUID(PLATFORM_USER_ID),
                org_id=UUID(PLATFORM_ORG_ID),
                password=SYSTEM_PASSWORD_HASH,
            ),
        )

    existing_template = conn.execute(
        sa.text("SELECT id FROM workflow_templates WHERE id = :id"),
        {"id": TEMPLATE_EPR_FULL},
    ).fetchone()
    if existing_template is None:
        op.bulk_insert(
            _WORKFLOW_TEMPLATES,
            [
                {
                    "id": UUID(TEMPLATE_EPR_FULL),
                    "org_id": UUID(PLATFORM_ORG_ID),
                    "owner_id": UUID(PLATFORM_USER_ID),
                    "name": "EPR Full Review",
                    "description": "Complete external paper review workflow across all EPR thread types.",
                    "module_type": "external_paper_review",
                    "scope": "platform",
                    "thread_sequence": [
                        "initial_read",
                        "methodology_review",
                        "literature_review",
                        "results_analysis",
                        "writing_quality",
                        "final_recommendation",
                    ],
                },
                {
                    "id": UUID(TEMPLATE_SPR_FULL),
                    "org_id": UUID(PLATFORM_ORG_ID),
                    "owner_id": UUID(PLATFORM_USER_ID),
                    "name": "SPR Full Evaluation",
                    "description": "Complete student paper review workflow for a single submission.",
                    "module_type": "student_paper_review",
                    "scope": "platform",
                    "thread_sequence": [
                        "submission_read",
                        "rubric_evaluation",
                        "feedback_generation",
                        "grade_recommendation",
                    ],
                },
            ],
        )

    existing_instruction = conn.execute(
        sa.text("SELECT id FROM instruction_sets WHERE id = :id"),
        {"id": INSTRUCTION_SET_INITIAL_READ},
    ).fetchone()
    if existing_instruction is None:
        op.bulk_insert(
            _INSTRUCTION_SETS,
            [
                {
                    "id": UUID(INSTRUCTION_SET_INITIAL_READ),
                    "org_id": UUID(PLATFORM_ORG_ID),
                    "level": "platform",
                    "thread_type": "initial_read",
                    "active_version_id": UUID(INSTRUCTION_VERSION_INITIAL_READ),
                },
                {
                    "id": UUID(INSTRUCTION_SET_FINAL),
                    "org_id": UUID(PLATFORM_ORG_ID),
                    "level": "platform",
                    "thread_type": "final_recommendation",
                    "active_version_id": UUID(INSTRUCTION_VERSION_FINAL),
                },
            ],
        )
        op.bulk_insert(
            _INSTRUCTION_VERSIONS,
            [
                {
                    "id": UUID(INSTRUCTION_VERSION_INITIAL_READ),
                    "instruction_set_id": UUID(INSTRUCTION_SET_INITIAL_READ),
                    "version_number": 1,
                    "content": (
                        "You are assisting an academic reviewer conducting an initial read of a "
                        "submitted manuscript. Summarize the paper's core contribution, methods, "
                        "and stated conclusions. Flag obvious scope or ethics concerns. Be precise "
                        "and cite specific sections when possible."
                    ),
                    "change_note": "MVP platform seed",
                    "created_by": UUID(PLATFORM_USER_ID),
                },
                {
                    "id": UUID(INSTRUCTION_VERSION_FINAL),
                    "instruction_set_id": UUID(INSTRUCTION_SET_FINAL),
                    "version_number": 1,
                    "content": (
                        "You are assisting an academic reviewer preparing a final recommendation. "
                        "Synthesize prior thread findings into a clear recommendation "
                        "(accept / minor revision / major revision / reject) with concise "
                        "rationale tied to evidence from the manuscript and review notes."
                    ),
                    "change_note": "MVP platform seed",
                    "created_by": UUID(PLATFORM_USER_ID),
                },
            ],
        )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM instruction_versions WHERE id IN (:v1, :v2)"
        ).bindparams(
            v1=UUID(INSTRUCTION_VERSION_INITIAL_READ),
            v2=UUID(INSTRUCTION_VERSION_FINAL),
        ),
    )
    op.execute(
        sa.text(
            "DELETE FROM instruction_sets WHERE id IN (:s1, :s2)"
        ).bindparams(
            s1=UUID(INSTRUCTION_SET_INITIAL_READ),
            s2=UUID(INSTRUCTION_SET_FINAL),
        ),
    )
    op.execute(
        sa.text(
            "DELETE FROM workflow_templates WHERE id IN (:t1, :t2)"
        ).bindparams(
            t1=UUID(TEMPLATE_EPR_FULL),
            t2=UUID(TEMPLATE_SPR_FULL),
        ),
    )
    op.execute(
        sa.text("DELETE FROM users WHERE id = :id").bindparams(id=UUID(PLATFORM_USER_ID)),
    )
