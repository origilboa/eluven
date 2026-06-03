"""Activity prompts, entity tags, and thread prompt usage.

Revision ID: 012
Revises: 011
Create Date: 2026-06-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_UUID = postgresql.UUID(as_uuid=True)
_NOW = sa.text("now()")

_PROMPT_TEXT_UPDATES: dict[str, str] = {
    "02000001-0001-4001-8001-000000000001": (
        "Assess the manuscript's overall contribution, significance, and fit for the target venue."
    ),
    "02000002-0001-4001-8001-000000000001": (
        "Identify the sections, claims, or figures that deserve closest scrutiny in this first pass."
    ),
    "02000003-0001-4001-8001-000000000001": (
        "Summarize the central thesis and flag major methodological or interpretive red flags."
    ),
    "02000004-0001-4001-8001-000000000001": (
        "Evaluate study design, sampling, and analysis choices against field standards."
    ),
    "02000005-0001-4001-8001-000000000001": (
        "Check compliance with applicable reporting standards indicated in task tags."
    ),
    "02000006-0001-4001-8001-000000000001": (
        "Assess threats to validity and whether limitations are acknowledged appropriately."
    ),
    "02000007-0001-4001-8001-000000000001": (
        "Evaluate how the manuscript positions itself against prior work in the field."
    ),
    "02000008-0001-4001-8001-000000000001": (
        "Identify missing or mischaracterized references that weaken the argument."
    ),
    "02000009-0001-4001-8001-000000000001": (
        "Assess novelty versus incremental advance relative to existing literature."
    ),
    "0200000a-0001-4001-8001-000000000001": (
        "Scrutinize primary outcomes, tables, and figures for accuracy and completeness."
    ),
    "0200000b-0001-4001-8001-000000000001": (
        "Evaluate whether effect sizes and statistical reporting support the authors' claims."
    ),
    "0200000c-0001-4001-8001-000000000001": (
        "Explore alternative explanations and whether limitations of the findings are discussed."
    ),
    "0200000d-0001-4001-8001-000000000001": (
        "Assess clarity, structure, and whether the tone suits the intended audience."
    ),
    "0200000e-0001-4001-8001-000000000001": (
        "Check adherence to journal structure and length expectations for the venue."
    ),
    "0200000f-0001-4001-8001-000000000001": (
        "Identify sections needing the most revision (abstract, figures, discussion)."
    ),
    "02000010-0001-4001-8001-000000000001": (
        "Draft a recommendation (accept, minor/major revision, reject) with explicit rationale."
    ),
    "02000011-0001-4001-8001-000000000001": (
        "List non-negotiable issues that must appear in the final recommendation."
    ),
    "02000012-0001-4001-8001-000000000001": (
        "Produce an editor-ready summary and/or letter to authors as appropriate."
    ),
    "02000013-0001-4001-8001-000000000001": (
        "Assess how well this submission meets the assignment brief and learning outcomes."
    ),
    "02000014-0001-4001-8001-000000000001": (
        "Apply rubric dimensions from assignment tags and identify strongest and weakest areas."
    ),
    "02000015-0001-4001-8001-000000000001": (
        "Frame the assessment using course level and discipline from assignment tags."
    ),
    "02000016-0001-4001-8001-000000000001": (
        "Score each rubric dimension with evidence from the submission."
    ),
    "02000017-0001-4001-8001-000000000001": (
        "Note any weighted, capped, or pass/fail criteria that affect the evaluation."
    ),
    "02000018-0001-4001-8001-000000000001": (
        "Flag borderline or failing performance that may require moderation."
    ),
    "02000019-0001-4001-8001-000000000001": (
        "Draft student-facing feedback in the tone specified in assignment tags."
    ),
    "0200001a-0001-4001-8001-000000000001": (
        "Keep feedback actionable while respecting institutional structure requirements."
    ),
    "0200001b-0001-4001-8001-000000000001": (
        "Prioritize detailed comments on the rubric criteria that matter most."
    ),
    "0200001c-0001-4001-8001-000000000001": (
        "Recommend a grade on the scale in assignment tags with rubric-mapped justification."
    ),
    "0200001d-0001-4001-8001-000000000001": (
        "Apply any late penalties or grade caps from submission and assignment tags."
    ),
    "0200001e-0001-4001-8001-000000000001": (
        "Summarize the grade recommendation with brief rubric-mapped rationale."
    ),
    "0200001f-0001-4001-8001-000000000001": (
        "Compare the resubmission against the prior version using submission metadata."
    ),
    "02000020-0001-4001-8001-000000000001": (
        "Account for any rubric or brief changes between submission versions."
    ),
    "02000021-0001-4001-8001-000000000001": (
        "Highlight improvements and remaining gaps against the brief and rubric."
    ),
}


def upgrade() -> None:
    op.add_column("clusters", sa.Column("structured_tags", postgresql.JSONB(), nullable=True))
    op.add_column(
        "clusters",
        sa.Column("freeform_tags", postgresql.ARRAY(sa.String()), nullable=True),
    )
    op.add_column("tasks", sa.Column("structured_tags", postgresql.JSONB(), nullable=True))
    op.add_column(
        "tasks",
        sa.Column("freeform_tags", postgresql.ARRAY(sa.String()), nullable=True),
    )
    op.add_column(
        "workflow_thread_executions",
        sa.Column("completed_prompt_count", sa.Integer(), server_default="0", nullable=False),
    )

    op.drop_index("ix_thread_qa_responses_thread_id", table_name="thread_qa_responses")
    op.drop_table("thread_qa_responses")

    op.rename_table("thread_qa_questions", "activity_prompts")
    op.alter_column("activity_prompts", "question_text", new_column_name="prompt_text")
    op.drop_column("activity_prompts", "is_required")
    op.drop_column("activity_prompts", "response_type")
    op.drop_column("activity_prompts", "options")

    op.create_table(
        "thread_prompt_usage",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("thread_id", _UUID, sa.ForeignKey("threads.id"), nullable=False),
        sa.Column("prompt_id", _UUID, sa.ForeignKey("activity_prompts.id"), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
    )
    op.create_index(
        "ix_thread_prompt_usage_thread_id",
        "thread_prompt_usage",
        ["thread_id"],
    )

    for prompt_id, prompt_text in _PROMPT_TEXT_UPDATES.items():
        op.execute(
            sa.text(
                "UPDATE activity_prompts SET prompt_text = :prompt_text WHERE id = :prompt_id",
            ).bindparams(prompt_text=prompt_text, prompt_id=prompt_id),
        )


def downgrade() -> None:
    op.drop_index("ix_thread_prompt_usage_thread_id", table_name="thread_prompt_usage")
    op.drop_table("thread_prompt_usage")

    op.add_column(
        "activity_prompts",
        sa.Column("options", postgresql.ARRAY(sa.String()), nullable=True),
    )
    op.add_column(
        "activity_prompts",
        sa.Column("response_type", sa.String(length=50), server_default="text", nullable=False),
    )
    op.add_column(
        "activity_prompts",
        sa.Column("is_required", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.alter_column("activity_prompts", "prompt_text", new_column_name="question_text")
    op.rename_table("activity_prompts", "thread_qa_questions")

    op.create_table(
        "thread_qa_responses",
        sa.Column("id", _UUID, primary_key=True),
        sa.Column("thread_id", _UUID, sa.ForeignKey("threads.id"), nullable=False),
        sa.Column("question_id", _UUID, sa.ForeignKey("thread_qa_questions.id"), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("response_options", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), server_default=_NOW, nullable=False),
    )
    op.create_index(
        "ix_thread_qa_responses_thread_id",
        "thread_qa_responses",
        ["thread_id"],
    )

    op.drop_column("workflow_thread_executions", "completed_prompt_count")
    op.drop_column("tasks", "freeform_tags")
    op.drop_column("tasks", "structured_tags")
    op.drop_column("clusters", "freeform_tags")
    op.drop_column("clusters", "structured_tags")
