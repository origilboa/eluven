"""Seed ActivityLibrary entries for External Paper Review (EPR).

Revision ID: 002
Revises: 001
Create Date: 2026-06-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLATFORM_ORG_ID = "00000000-0000-0000-0000-000000000001"
MODULE_TYPE = "external_paper_review"
SCOPE = "platform"
DEFAULT_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
HAIKU_FALLBACK_MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"

# Fixed UUIDs for idempotent reference in downgrade and documentation.
ENTRY_INITIAL_READ = "01000001-0001-4001-8001-000000000001"
ENTRY_METHODOLOGY = "01000002-0001-4001-8001-000000000001"
ENTRY_LITERATURE = "01000003-0001-4001-8001-000000000001"
ENTRY_RESULTS = "01000004-0001-4001-8001-000000000001"
ENTRY_WRITING = "01000005-0001-4001-8001-000000000001"
ENTRY_FINAL = "01000006-0001-4001-8001-000000000001"

_ACTIVITY_LIBRARY = sa.table(
    "activity_library_entries",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("org_id", postgresql.UUID(as_uuid=True)),
    sa.column("thread_type", sa.String),
    sa.column("module_type", sa.String),
    sa.column("display_name", sa.String),
    sa.column("description", sa.Text),
    sa.column("scope", sa.String),
    sa.column("is_active", sa.Boolean),
    sa.column("default_model_id", sa.String),
    sa.column("fallback_model_id", sa.String),
    sa.column("token_budget", sa.Integer),
    sa.column("supports_automation", sa.Boolean),
)

_QA_QUESTIONS = sa.table(
    "thread_qa_questions",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("activity_entry_id", postgresql.UUID(as_uuid=True)),
    sa.column("question_text", sa.Text),
    sa.column("stage", sa.String),
    sa.column("response_type", sa.String),
    sa.column("is_required", sa.Boolean),
    sa.column("sequence_index", sa.Integer),
)

_ACTIVITY_ROWS: list[dict[str, object]] = [
    {
        "id": ENTRY_INITIAL_READ,
        "thread_type": "initial_read",
        "display_name": "Initial Read",
        "token_budget": 20_000,
        "fallback_model_id": None,
    },
    {
        "id": ENTRY_METHODOLOGY,
        "thread_type": "methodology_review",
        "display_name": "Methodology Review",
        "token_budget": 30_000,
        "fallback_model_id": None,
    },
    {
        "id": ENTRY_LITERATURE,
        "thread_type": "literature_review",
        "display_name": "Literature Review",
        "token_budget": 25_000,
        "fallback_model_id": None,
    },
    {
        "id": ENTRY_RESULTS,
        "thread_type": "results_analysis",
        "display_name": "Results Analysis",
        "token_budget": 25_000,
        "fallback_model_id": None,
    },
    {
        "id": ENTRY_WRITING,
        "thread_type": "writing_quality",
        "display_name": "Writing Quality",
        "token_budget": 15_000,
        "fallback_model_id": None,
    },
    {
        "id": ENTRY_FINAL,
        "thread_type": "final_recommendation",
        "display_name": "Final Recommendation",
        "token_budget": 15_000,
        "fallback_model_id": HAIKU_FALLBACK_MODEL_ID,
    },
]

_QA_ROWS: list[dict[str, object]] = [
    # initial_read
    {
        "id": "02000001-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_INITIAL_READ,
        "sequence_index": 0,
        "question_text": (
            "What is your primary focus for this initial read "
            "(e.g., overall contribution, venue fit, major red flags)?"
        ),
    },
    {
        "id": "02000002-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_INITIAL_READ,
        "sequence_index": 1,
        "question_text": (
            "Are there specific sections, claims, or figures you want prioritised in this first pass?"
        ),
    },
    {
        "id": "02000003-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_INITIAL_READ,
        "sequence_index": 2,
        "question_text": (
            "What deadline or editorial decision context should shape the depth of this review?"
        ),
    },
    # methodology_review
    {
        "id": "02000004-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_METHODOLOGY,
        "sequence_index": 0,
        "question_text": (
            "Which methodological aspects matter most for your evaluation "
            "(design, sampling, analysis, validity threats)?"
        ),
    },
    {
        "id": "02000005-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_METHODOLOGY,
        "sequence_index": 1,
        "question_text": (
            "Should the review be judged against specific reporting standards "
            "(e.g., CONSORT, STROBE, PRISMA, ARRIVE)?"
        ),
    },
    {
        "id": "02000006-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_METHODOLOGY,
        "sequence_index": 2,
        "question_text": (
            "What level of statistical or methodological detail should the review assume for the intended audience?"
        ),
    },
    # literature_review
    {
        "id": "02000007-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_LITERATURE,
        "sequence_index": 0,
        "question_text": (
            "Which bodies of literature are most relevant for positioning this manuscript?"
        ),
    },
    {
        "id": "02000008-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_LITERATURE,
        "sequence_index": 1,
        "question_text": (
            "Are there seminal papers or recent reviews you already treat as essential benchmarks?"
        ),
    },
    {
        "id": "02000009-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_LITERATURE,
        "sequence_index": 2,
        "question_text": (
            "Should the review emphasise novelty, incremental advance, or gap-filling relative to prior work?"
        ),
    },
    # results_analysis
    {
        "id": "0200000a-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_RESULTS,
        "sequence_index": 0,
        "question_text": (
            "Which results (tables, figures, primary outcomes) should receive the closest scrutiny?"
        ),
    },
    {
        "id": "0200000b-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_RESULTS,
        "sequence_index": 1,
        "question_text": (
            "Are there concerns about interpretation, effect sizes, or statistical reporting you want highlighted?"
        ),
    },
    {
        "id": "0200000c-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_RESULTS,
        "sequence_index": 2,
        "question_text": (
            "Should alternative explanations and limitations of the findings be explored explicitly?"
        ),
    },
    # writing_quality
    {
        "id": "0200000d-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_WRITING,
        "sequence_index": 0,
        "question_text": (
            "Who is the intended audience, and what clarity or tone standards should apply?"
        ),
    },
    {
        "id": "0200000e-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_WRITING,
        "sequence_index": 1,
        "question_text": (
            "Are there journal-specific structure, length, or style requirements to apply?"
        ),
    },
    {
        "id": "0200000f-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_WRITING,
        "sequence_index": 2,
        "question_text": (
            "Which sections need the most attention (abstract, figures, discussion, language editing)?"
        ),
    },
    # final_recommendation
    {
        "id": "02000010-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_FINAL,
        "sequence_index": 0,
        "question_text": (
            "What decision framework should guide the recommendation "
            "(accept, minor/major revision, reject)?"
        ),
    },
    {
        "id": "02000011-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_FINAL,
        "sequence_index": 1,
        "question_text": (
            "Are there non-negotiable issues that must appear in the final recommendation?"
        ),
    },
    {
        "id": "02000012-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_FINAL,
        "sequence_index": 2,
        "question_text": (
            "What output format do you need (editor summary, letter to authors, or both)?"
        ),
    },
]


def _activity_insert_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for spec in _ACTIVITY_ROWS:
        rows.append(
            {
                "id": spec["id"],
                "org_id": PLATFORM_ORG_ID,
                "thread_type": spec["thread_type"],
                "module_type": MODULE_TYPE,
                "display_name": spec["display_name"],
                "description": None,
                "scope": SCOPE,
                "is_active": True,
                "default_model_id": DEFAULT_MODEL_ID,
                "fallback_model_id": spec["fallback_model_id"],
                "token_budget": spec["token_budget"],
                "supports_automation": True,
            },
        )
    return rows


def _qa_insert_rows() -> list[dict[str, object]]:
    return [
        {
            "id": row["id"],
            "activity_entry_id": row["activity_entry_id"],
            "question_text": row["question_text"],
            "stage": "opening",
            "response_type": "text",
            "is_required": True,
            "sequence_index": row["sequence_index"],
        }
        for row in _QA_ROWS
    ]


def upgrade() -> None:
    op.bulk_insert(_ACTIVITY_LIBRARY, _activity_insert_rows())
    op.bulk_insert(_QA_QUESTIONS, _qa_insert_rows())


def downgrade() -> None:
    # Remove dependent Q&A responses first (if any exist in dev/test data).
    op.execute(
        f"""
        DELETE FROM thread_qa_responses
        WHERE question_id IN (
            SELECT q.id
            FROM thread_qa_questions q
            INNER JOIN activity_library_entries e ON e.id = q.activity_entry_id
            WHERE e.org_id = '{PLATFORM_ORG_ID}'
              AND e.module_type = '{MODULE_TYPE}'
        )
        """,
    )
    op.execute(
        f"""
        DELETE FROM thread_qa_questions
        WHERE activity_entry_id IN (
            SELECT id FROM activity_library_entries
            WHERE org_id = '{PLATFORM_ORG_ID}'
              AND module_type = '{MODULE_TYPE}'
        )
        """,
    )
    op.execute(
        f"""
        DELETE FROM activity_library_entries
        WHERE org_id = '{PLATFORM_ORG_ID}'
          AND module_type = '{MODULE_TYPE}'
        """,
    )
