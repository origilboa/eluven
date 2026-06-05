"""Tests for instruction authoring assistant helpers."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from botocore.exceptions import ClientError  # pyright: ignore[reportMissingTypeStubs]

from models.instruction import InstructionLevel
from services.instructions.authoring_assistant import _bedrock_stream_error_message
from services.instructions.authoring_context import (
    _format_activity_configuration,
    _session_block,
)
from models.activity import ActivityLibraryEntry
from services.instructions.prompt_loader import (
    charter_version_from_text,
    load_charter_text,
    load_level_brief,
)


def test_bedrock_stream_error_message_use_case_form() -> None:
    exc = ClientError(
        {
            "Error": {
                "Code": "ResourceNotFoundException",
                "Message": (
                    "Model use case details have not been submitted for this account."
                ),
            },
        },
        "InvokeModelWithResponseStream",
    )
    message = _bedrock_stream_error_message(exc)
    assert "use-case form" in message


def test_charter_version_from_text() -> None:
    text = "# Title\n\n**Version:** 1.2.3\n\nBody"
    assert charter_version_from_text(text) == "1.2.3"


def test_charter_version_unknown_when_missing() -> None:
    assert charter_version_from_text("# No version") == "unknown"


def test_load_charter_text_from_repo() -> None:
    text = load_charter_text()
    assert "Instruction Authoring Assistant" in text
    assert charter_version_from_text(text) == "1.1.0"
    assert "Activity configuration vs InstructionLayer" in text
    assert "Integrity review mode" in text


def test_session_block_integrity_review_active() -> None:
    block = _session_block(
        editable_level=InstructionLevel.USER,
        locale="en",
        integrity_review=True,
    )
    assert "Integrity review: active" in block


def test_format_activity_configuration_includes_settings_fields() -> None:
    entry = ActivityLibraryEntry(
        org_id=uuid4(),
        thread_type="initial_read",
        module_type="external_paper_review",
        display_name="Initial read",
        scope="platform",
        default_model_id="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        token_budget=50000,
        supports_automation=True,
    )
    block = _format_activity_configuration(entry)
    assert "Settings tab" in block
    assert "default_model_id" in block
    assert "token_budget: 50000" in block


@pytest.mark.parametrize(
    "level",
    [
        InstructionLevel.PLATFORM,
        InstructionLevel.ORG,
        InstructionLevel.USER,
        InstructionLevel.CLUSTER,
        InstructionLevel.TASK,
        InstructionLevel.THREAD,
    ],
)
def test_load_level_briefs_exist(level: InstructionLevel) -> None:
    brief = load_level_brief(level)
    assert brief.strip()
    assert f"Level brief — {level.value}" in brief


def test_repo_charter_file_exists() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    charter = repo_root / "docs" / "instructions" / "authoring-agent-charter.md"
    assert charter.is_file()
