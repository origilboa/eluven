"""Tests for instruction authoring assistant helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from models.instruction import InstructionLevel
from services.instructions.prompt_loader import (
    charter_version_from_text,
    load_charter_text,
    load_level_brief,
)


def test_charter_version_from_text() -> None:
    text = "# Title\n\n**Version:** 1.2.3\n\nBody"
    assert charter_version_from_text(text) == "1.2.3"


def test_charter_version_unknown_when_missing() -> None:
    assert charter_version_from_text("# No version") == "unknown"


def test_load_charter_text_from_repo() -> None:
    text = load_charter_text()
    assert "Instruction Authoring Assistant" in text
    assert charter_version_from_text(text) == "1.0.0"


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
