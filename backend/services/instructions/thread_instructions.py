"""Per-thread instruction set creation from ActivityLibrary defaults."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from models.activity import ActivityLibraryEntry
from models.instruction import InstructionLevel, InstructionSet, InstructionVersion
from models.thread import Thread

logger = get_logger(__name__)

_CHANGE_NOTE_FROM_ACTIVITY = "Copied from activity type default on thread create"


def default_content_from_activity(activity: ActivityLibraryEntry | None) -> str:
    """Return trimmed default instruction text for an activity type."""
    if activity is None or not activity.default_instruction_content:
        return ""
    return activity.default_instruction_content.strip()


async def create_thread_instruction_set(
    session: AsyncSession,
    *,
    thread: Thread,
    org_id: UUID,
    created_by: UUID,
    activity: ActivityLibraryEntry | None,
    change_note: str = _CHANGE_NOTE_FROM_ACTIVITY,
) -> InstructionSet:
    """Create thread-level instruction set v1 from activity default content."""
    content = default_content_from_activity(activity)

    instruction_set = InstructionSet(
        org_id=org_id,
        level=InstructionLevel.THREAD,
        thread_id=thread.id,
    )
    session.add(instruction_set)
    await session.flush()

    version = InstructionVersion(
        instruction_set_id=instruction_set.id,
        version_number=1,
        content=content,
        change_note=change_note,
        created_by=created_by,
    )
    session.add(version)
    await session.flush()

    instruction_set.active_version_id = version.id
    await session.flush()

    logger.info(
        "thread_instruction_set_created",
        thread_id=str(thread.id),
        instruction_set_id=str(instruction_set.id),
        version_id=str(version.id),
        content_length=len(content),
    )
    return instruction_set


async def get_thread_instruction_set(
    session: AsyncSession,
    *,
    thread_id: UUID,
    org_id: UUID,
) -> InstructionSet | None:
    """Load thread-level instruction set if it exists."""
    result = await session.execute(
        select(InstructionSet).where(
            InstructionSet.level == InstructionLevel.THREAD,
            InstructionSet.thread_id == thread_id,
            InstructionSet.org_id == org_id,
        ).limit(1),
    )
    return result.scalar_one_or_none()
