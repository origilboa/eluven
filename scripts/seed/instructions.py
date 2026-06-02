"""Seed sample cluster and task instructions for MVP testing."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from models.cluster import Cluster
from models.instruction import (
    InstructionLevel,
    InstructionSet,
    InstructionVersion,
    TaskThreadTypeInstruction,
)
from models.task import Task
from models.user import User
from seed.constants import DEV_USER_EMAIL

logger = get_logger(__name__)

_DEMO_MARKER = "Demo "
_SEED_CHANGE_NOTE = "seed_demo_instructions"

CLUSTER_INSTRUCTION_ALL = """\
Assignment: Research Methods 101 — shared evaluation instructions

Apply this rubric consistently across every submission in this assignment:
- Thesis clarity (25%)
- Evidence and citations (25%)
- Structure and flow (25%)
- Writing quality (25%)

Tone: constructive and specific. Tie feedback to rubric criteria.
Record graded judgments as TaskMemory findings; do not output final letter grades in chat.\
"""

CLUSTER_INSTRUCTION_RUBRIC = """\
For rubric_evaluation threads only:

Score each rubric dimension 1–4 (1=needs major revision, 4=exemplary).
Justify each score with one concrete example from the submission.
If evidence is missing for a dimension, note it as a gap in TaskMemory.\
"""

EPR_TASK_INSTRUCTION = """\
Task focus: external review of a hybrid recommender systems manuscript.

Prioritize in this order:
1. Validity of the within-subjects design and sample size justification
2. Whether baselines reflect current literature (2023+)
3. Practical vs statistical significance of reported effects

Flag any claim not clearly supported by data or methods.\
"""

EPR_THREAD_ADDENDUM_INITIAL_READ = """\
Initial read only: open with a one-paragraph executive summary, then list exactly three
follow-up questions you would ask the authors before deeper methodology review.\
"""

SPR_TASK_INSTRUCTION = """\
Student submission review — compare against the assignment cluster rubric.

This is a draft-stage submission: be encouraging while naming the top two revision priorities.
Use supportive language appropriate for undergraduate feedback.\
"""

SPR_THREAD_ADDENDUM_SUBMISSION_READ = """\
Submission read: summarize the student's thesis in one sentence, then assess whether the
introduction states scope and contribution clearly enough for a methods course essay.\
"""

GENERIC_EPR_TEST_TASK = """\
Sample task instructions (seeded for testing).

Treat this as an external paper review. Be concise, evidence-based, and structured.
When uncertain, ask a clarifying question rather than assuming.\
"""

ORG_INSTRUCTION = """\
Dev organization defaults for internal MVP testing.

Reviews should follow APA-aware academic tone. Prefer bullet findings in TaskMemory.
Escalate ethical concerns explicitly rather than burying them in general comments.\
"""

USER_INSTRUCTION = """\
Personal preferences for dev@eluven.ai during internal testing.

Keep responses under 400 words unless summarizing a full section.
Always end thread responses with a numbered list of suggested next steps.\
"""


async def seed_sample_instructions_for_session(session: AsyncSession) -> int:
    """Seed instructions without committing — for use inside demo seed."""
    result = await session.execute(select(User).where(User.email == DEV_USER_EMAIL))
    dev_user = result.scalar_one_or_none()
    if dev_user is None:
        logger.warning("seed_instructions_skipped", reason="dev_user_missing")
        return 0

    seeded_count = 0

    if await _ensure_versioned_instruction(
        session,
        level=InstructionLevel.ORG,
        org_id=dev_user.org_id,
        created_by=dev_user.id,
        owner_org_id=dev_user.org_id,
        thread_type=None,
        content=ORG_INSTRUCTION,
    ):
        seeded_count += 1

    if await _ensure_versioned_instruction(
        session,
        level=InstructionLevel.USER,
        org_id=dev_user.org_id,
        created_by=dev_user.id,
        user_id=dev_user.id,
        thread_type=None,
        content=USER_INSTRUCTION,
    ):
        seeded_count += 1

    cluster_result = await session.execute(
        select(Cluster).where(
            Cluster.owner_id == dev_user.id,
            Cluster.name == f"{_DEMO_MARKER}Assignment — Research Methods 101",
        ),
    )
    assignment = cluster_result.scalar_one_or_none()
    if assignment is not None:
        if await _ensure_versioned_instruction(
            session,
            level=InstructionLevel.CLUSTER,
            org_id=dev_user.org_id,
            created_by=dev_user.id,
            cluster_id=assignment.id,
            thread_type=None,
            content=CLUSTER_INSTRUCTION_ALL,
        ):
            seeded_count += 1
        if await _ensure_versioned_instruction(
            session,
            level=InstructionLevel.CLUSTER,
            org_id=dev_user.org_id,
            created_by=dev_user.id,
            cluster_id=assignment.id,
            thread_type="rubric_evaluation",
            content=CLUSTER_INSTRUCTION_RUBRIC,
        ):
            seeded_count += 1

    epr_result = await session.execute(
        select(Task).where(
            Task.owner_id == dev_user.id,
            Task.title == f"{_DEMO_MARKER}EPR — Methods paper (in progress)",
        ),
    )
    epr_task = epr_result.scalar_one_or_none()
    if epr_task is not None:
        if await _ensure_versioned_instruction(
            session,
            level=InstructionLevel.TASK,
            org_id=dev_user.org_id,
            created_by=dev_user.id,
            task_id=epr_task.id,
            thread_type=None,
            content=EPR_TASK_INSTRUCTION,
        ):
            seeded_count += 1
        if await _ensure_thread_type_addendum(
            session,
            task_id=epr_task.id,
            thread_type="initial_read",
            content=EPR_THREAD_ADDENDUM_INITIAL_READ,
            created_by=dev_user.id,
        ):
            seeded_count += 1

    spr_result = await session.execute(
        select(Task).where(
            Task.owner_id == dev_user.id,
            Task.title == f"{_DEMO_MARKER}SPR — Alice Chen submission",
        ),
    )
    spr_task = spr_result.scalar_one_or_none()
    if spr_task is not None:
        if await _ensure_versioned_instruction(
            session,
            level=InstructionLevel.TASK,
            org_id=dev_user.org_id,
            created_by=dev_user.id,
            task_id=spr_task.id,
            thread_type=None,
            content=SPR_TASK_INSTRUCTION,
        ):
            seeded_count += 1
        if await _ensure_thread_type_addendum(
            session,
            task_id=spr_task.id,
            thread_type="submission_read",
            content=SPR_THREAD_ADDENDUM_SUBMISSION_READ,
            created_by=dev_user.id,
        ):
            seeded_count += 1

    test_result = await session.execute(
        select(Task).where(
            Task.owner_id == dev_user.id,
            Task.title == "test",
            Task.module_type == "external_paper_review",
        ),
    )
    test_task = test_result.scalar_one_or_none()
    if test_task is not None:
        if await _ensure_versioned_instruction(
            session,
            level=InstructionLevel.TASK,
            org_id=dev_user.org_id,
            created_by=dev_user.id,
            task_id=test_task.id,
            thread_type=None,
            content=GENERIC_EPR_TEST_TASK,
        ):
            seeded_count += 1

    sample_epr_result = await session.execute(
        select(Task).where(
            Task.owner_id == dev_user.id,
            Task.title == "Sample Paper Review",
            Task.module_type == "external_paper_review",
        ),
    )
    sample_epr = sample_epr_result.scalar_one_or_none()
    if sample_epr is not None:
        if await _ensure_versioned_instruction(
            session,
            level=InstructionLevel.TASK,
            org_id=dev_user.org_id,
            created_by=dev_user.id,
            task_id=sample_epr.id,
            thread_type=None,
            content=GENERIC_EPR_TEST_TASK,
        ):
            seeded_count += 1

    return seeded_count


async def seed_sample_instructions_async(session: AsyncSession) -> None:
    """Seed idempotent sample instructions and commit."""
    seeded_count = await seed_sample_instructions_for_session(session)
    await session.commit()
    logger.info("seed_sample_instructions_complete", seeded_count=seeded_count)


async def _instruction_set_query(
    *,
    level: InstructionLevel,
    org_id: UUID,
    cluster_id: UUID | None = None,
    task_id: UUID | None = None,
    thread_type: str | None = None,
):
    query = select(InstructionSet).where(
        InstructionSet.level == level,
        InstructionSet.org_id == org_id,
    )
    if cluster_id is not None:
        query = query.where(InstructionSet.cluster_id == cluster_id)
    if task_id is not None:
        query = query.where(InstructionSet.task_id == task_id)
    if thread_type is None:
        query = query.where(InstructionSet.thread_type.is_(None))
    else:
        query = query.where(InstructionSet.thread_type == thread_type)
    return query


async def _ensure_versioned_instruction(
    session: AsyncSession,
    *,
    level: InstructionLevel,
    org_id: UUID,
    created_by: UUID,
    content: str,
    cluster_id: UUID | None = None,
    task_id: UUID | None = None,
    thread_type: str | None = None,
    owner_org_id: UUID | None = None,
    user_id: UUID | None = None,
) -> bool:
    """Create instruction set + v1 if no active version exists. Returns True if created."""
    query = select(InstructionSet).where(
        InstructionSet.level == level,
        InstructionSet.org_id == org_id,
    )
    if cluster_id is not None:
        query = query.where(InstructionSet.cluster_id == cluster_id)
    if task_id is not None:
        query = query.where(InstructionSet.task_id == task_id)
    if owner_org_id is not None:
        query = query.where(InstructionSet.owner_org_id == owner_org_id)
    if user_id is not None:
        query = query.where(InstructionSet.user_id == user_id)
    if thread_type is None:
        query = query.where(InstructionSet.thread_type.is_(None))
    else:
        query = query.where(InstructionSet.thread_type == thread_type)
    if cluster_id is None:
        query = query.where(InstructionSet.cluster_id.is_(None))
    if task_id is None:
        query = query.where(InstructionSet.task_id.is_(None))
    result = await session.execute(query.limit(1))
    instruction_set = result.scalar_one_or_none()

    if instruction_set is not None and instruction_set.active_version_id is not None:
        return False

    if instruction_set is None:
        instruction_set = InstructionSet(
            org_id=org_id,
            level=level,
            cluster_id=cluster_id,
            task_id=task_id,
            thread_type=thread_type,
            owner_org_id=owner_org_id,
            user_id=user_id,
        )
        session.add(instruction_set)
        await session.flush()

    version = InstructionVersion(
        instruction_set_id=instruction_set.id,
        version_number=1,
        content=content,
        change_note=_SEED_CHANGE_NOTE,
        created_by=created_by,
    )
    session.add(version)
    await session.flush()
    instruction_set.active_version_id = version.id
    await session.flush()

    logger.info(
        "seed_instruction_created",
        level=level.value,
        cluster_id=str(cluster_id) if cluster_id else None,
        task_id=str(task_id) if task_id else None,
        thread_type=thread_type,
    )
    return True


async def _ensure_thread_type_addendum(
    session: AsyncSession,
    *,
    task_id: UUID,
    thread_type: str,
    content: str,
    created_by: UUID,
) -> bool:
    result = await session.execute(
        select(TaskThreadTypeInstruction).where(
            TaskThreadTypeInstruction.task_id == task_id,
            TaskThreadTypeInstruction.thread_type == thread_type,
        ),
    )
    if result.scalar_one_or_none() is not None:
        return False

    session.add(
        TaskThreadTypeInstruction(
            task_id=task_id,
            thread_type=thread_type,
            content=content,
            created_by=created_by,
        ),
    )
    await session.flush()
    logger.info(
        "seed_thread_addendum_created",
        task_id=str(task_id),
        thread_type=thread_type,
    )
    return True
