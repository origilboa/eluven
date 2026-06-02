"""Tests for per-thread instruction creation from activity defaults."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from models.activity import ActivityLibraryEntry
from models.instruction import InstructionLevel, InstructionSet, InstructionVersion
from models.thread import Thread
from services.instructions.thread_instructions import (
    create_thread_instruction_set,
    default_content_from_activity,
)


def test_default_content_from_activity_empty_when_missing() -> None:
    assert default_content_from_activity(None) == ""
    entry = MagicMock(spec=ActivityLibraryEntry)
    entry.default_instruction_content = None
    assert default_content_from_activity(entry) == ""


def test_default_content_from_activity_trims() -> None:
    entry = MagicMock(spec=ActivityLibraryEntry)
    entry.default_instruction_content = "  Review the methods.  "
    assert default_content_from_activity(entry) == "Review the methods."


@pytest.mark.asyncio
async def test_create_thread_instruction_set_persists_version() -> None:
    thread_id = uuid4()
    org_id = uuid4()
    user_id = uuid4()
    thread = Thread(
        id=thread_id,
        org_id=org_id,
        task_id=uuid4(),
        owner_id=user_id,
        title="Test",
        thread_type="initial_read",
    )
    activity = MagicMock(spec=ActivityLibraryEntry)
    activity.default_instruction_content = "Default thread prompt."

    session = AsyncMock()
    added: list[object] = []

    def capture_add(obj: object) -> None:
        added.append(obj)

    session.add = MagicMock(side_effect=capture_add)
    session.flush = AsyncMock()

    result = await create_thread_instruction_set(
        session,
        thread=thread,
        org_id=org_id,
        created_by=user_id,
        activity=activity,
    )

    assert isinstance(result, InstructionSet)
    assert result.level == InstructionLevel.THREAD
    assert result.thread_id == thread_id
    instruction_sets = [obj for obj in added if isinstance(obj, InstructionSet)]
    versions = [obj for obj in added if isinstance(obj, InstructionVersion)]
    assert len(instruction_sets) == 1
    assert len(versions) == 1
    assert versions[0].content == "Default thread prompt."
    assert versions[0].version_number == 1
    assert result.active_version_id == versions[0].id
