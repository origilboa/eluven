"""Sync InstructionSet from ActivityLibrary default_instruction_content."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from models.activity import ActivityLibraryEntry
from models.instruction import InstructionLevel, InstructionSet, InstructionVersion

logger = get_logger(__name__)

_DEFAULT_CHANGE_NOTE = "Synced from Activity Library"


async def sync_instruction_set_from_activity_default(
    session: AsyncSession,
    *,
    entry: ActivityLibraryEntry,
    content: str | None,
    user_id: UUID,
    change_note: str = _DEFAULT_CHANGE_NOTE,
) -> None:
    """Upsert platform/org InstructionSet for this thread_type when content is set."""
    stripped = (content or "").strip()
    if not stripped:
        return

    level = InstructionLevel.PLATFORM if entry.scope == "platform" else InstructionLevel.ORG

    query = select(InstructionSet).where(
        InstructionSet.level == level,
        InstructionSet.org_id == entry.org_id,
        InstructionSet.thread_type == entry.thread_type,
    )
    if level == InstructionLevel.ORG:
        query = query.where(InstructionSet.owner_org_id == entry.org_id)

    result = await session.execute(query.limit(1))
    instruction_set = result.scalar_one_or_none()

    if instruction_set is None:
        instruction_set = InstructionSet(
            org_id=entry.org_id,
            level=level,
            thread_type=entry.thread_type,
            owner_org_id=entry.org_id if level == InstructionLevel.ORG else None,
        )
        session.add(instruction_set)
        await session.flush()

    if instruction_set.active_version_id is not None:
        active = await session.get(InstructionVersion, instruction_set.active_version_id)
        if active is not None and active.content.strip() == stripped:
            return

    max_version = await session.scalar(
        select(func.max(InstructionVersion.version_number)).where(
            InstructionVersion.instruction_set_id == instruction_set.id,
        ),
    )
    next_version = int(max_version or 0) + 1

    version = InstructionVersion(
        instruction_set_id=instruction_set.id,
        version_number=next_version,
        content=stripped,
        change_note=change_note,
        created_by=user_id,
    )
    session.add(version)
    await session.flush()
    instruction_set.active_version_id = version.id

    logger.info(
        "activity_instruction_set_synced",
        entry_id=str(entry.id),
        instruction_set_id=str(instruction_set.id),
        version_number=next_version,
        level=level.value,
        thread_type=entry.thread_type,
    )
