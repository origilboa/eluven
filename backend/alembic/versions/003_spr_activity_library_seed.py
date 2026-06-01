"""Seed ActivityLibrary entries for Student Paper Review (SPR).

Revision ID: 003
Revises: 002
Create Date: 2026-06-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLATFORM_ORG_ID = "00000000-0000-0000-0000-000000000001"
MODULE_TYPE = "student_paper_review"
SCOPE = "platform"
DEFAULT_MODEL_ID = "anthropic.claude-3-5-sonnet-20241022-v2:0"
HAIKU_FALLBACK_MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"

# Fixed UUIDs (SPR range — distinct from EPR migration 002).
ENTRY_SUBMISSION_READ = "01000011-0001-4001-8001-000000000001"
ENTRY_RUBRIC_EVALUATION = "01000012-0001-4001-8001-000000000001"
ENTRY_FEEDBACK_GENERATION = "01000013-0001-4001-8001-000000000001"
ENTRY_GRADE_RECOMMENDATION = "01000014-0001-4001-8001-000000000001"
ENTRY_VERSION_COMPARISON = "01000015-0001-4001-8001-000000000001"

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
        "id": ENTRY_SUBMISSION_READ,
        "thread_type": "submission_read",
        "display_name": "Submission Read",
        "token_budget": 20_000,
        "fallback_model_id": None,
    },
    {
        "id": ENTRY_RUBRIC_EVALUATION,
        "thread_type": "rubric_evaluation",
        "display_name": "Rubric Evaluation",
        "token_budget": 30_000,
        "fallback_model_id": None,
    },
    {
        "id": ENTRY_FEEDBACK_GENERATION,
        "thread_type": "feedback_generation",
        "display_name": "Feedback Generation",
        "token_budget": 25_000,
        "fallback_model_id": None,
    },
    {
        "id": ENTRY_GRADE_RECOMMENDATION,
        "thread_type": "grade_recommendation",
        "display_name": "Grade Recommendation",
        "token_budget": 15_000,
        "fallback_model_id": HAIKU_FALLBACK_MODEL_ID,
    },
    {
        "id": ENTRY_VERSION_COMPARISON,
        "thread_type": "version_comparison",
        "display_name": "Version Comparison",
        "token_budget": 30_000,
        "fallback_model_id": None,
    },
]

_QA_ROWS: list[dict[str, object]] = [
    # submission_read
    {
        "id": "02000013-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_SUBMISSION_READ,
        "sequence_index": 0,
        "question_text": (
            "What are the key learning outcomes or requirements from the assignment brief "
            "for this submission?"
        ),
    },
    {
        "id": "02000014-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_SUBMISSION_READ,
        "sequence_index": 1,
        "question_text": (
            "Is there a rubric or marking scheme to apply, and which criteria matter most "
            "for this first read?"
        ),
    },
    {
        "id": "02000015-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_SUBMISSION_READ,
        "sequence_index": 2,
        "question_text": (
            "What course level and disciplinary context should frame this initial assessment?"
        ),
    },
    # rubric_evaluation
    {
        "id": "02000016-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_RUBRIC_EVALUATION,
        "sequence_index": 0,
        "question_text": (
            "Summarise or confirm the rubric dimensions to apply "
            "(or note that the uploaded rubric is authoritative)."
        ),
    },
    {
        "id": "02000017-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_RUBRIC_EVALUATION,
        "sequence_index": 1,
        "question_text": (
            "Are any rubric criteria weighted differently, capped, or treated as pass/fail?"
        ),
    },
    {
        "id": "02000018-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_RUBRIC_EVALUATION,
        "sequence_index": 2,
        "question_text": (
            "Should borderline or failing performance be flagged for moderation before feedback is drafted?"
        ),
    },
    # feedback_generation
    {
        "id": "02000019-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_FEEDBACK_GENERATION,
        "sequence_index": 0,
        "question_text": (
            "What tone should student-facing feedback use "
            "(formative, summative, encouraging, direct)?"
        ),
    },
    {
        "id": "0200001a-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_FEEDBACK_GENERATION,
        "sequence_index": 1,
        "question_text": (
            "Are there institutional requirements for feedback length, structure, "
            "or prohibitions (e.g., no predicted grades in comments)?"
        ),
    },
    {
        "id": "0200001b-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_FEEDBACK_GENERATION,
        "sequence_index": 2,
        "question_text": (
            "Which rubric criteria or assignment tasks should receive the most detailed comments?"
        ),
    },
    # grade_recommendation
    {
        "id": "0200001c-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_GRADE_RECOMMENDATION,
        "sequence_index": 0,
        "question_text": (
            "What grading scale applies (letter grades, percentages, pass/fail, honours bands)?"
        ),
    },
    {
        "id": "0200001d-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_GRADE_RECOMMENDATION,
        "sequence_index": 1,
        "question_text": (
            "Are there grade caps, late penalties, or moderation bands the recommendation must respect?"
        ),
    },
    {
        "id": "0200001e-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_GRADE_RECOMMENDATION,
        "sequence_index": 2,
        "question_text": (
            "Should the recommendation include a brief justification mapped to the rubric?"
        ),
    },
    # version_comparison
    {
        "id": "0200001f-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_VERSION_COMPARISON,
        "sequence_index": 0,
        "question_text": (
            "Which submission version is the baseline (original vs resubmission) for this comparison?"
        ),
    },
    {
        "id": "02000020-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_VERSION_COMPARISON,
        "sequence_index": 1,
        "question_text": (
            "Did the assignment brief or rubric change between versions, and how should that affect the comparison?"
        ),
    },
    {
        "id": "02000021-0001-4001-8001-000000000001",
        "activity_entry_id": ENTRY_VERSION_COMPARISON,
        "sequence_index": 2,
        "question_text": (
            "Should the comparison highlight improvements only, or also remaining gaps against the brief and rubric?"
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
