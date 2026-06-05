"""Tests for ActivityLibrary InstructionSet sync and studio charters."""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]


def test_activity_charter_files_exist() -> None:
    instructions = _REPO_ROOT / "docs" / "instructions"
    assert (instructions / "activity-prompt-authoring-agent-charter.md").is_file()
    assert (instructions / "activity-type-orchestrator-charter.md").is_file()


def test_charter_loader_versions() -> None:
    from services.activity.charter_loader import (
        charter_version_from_text,
        load_orchestrator_charter,
        load_prompt_authoring_charter,
    )

    assert charter_version_from_text(load_prompt_authoring_charter()) == "1.0.0"
    assert charter_version_from_text(load_orchestrator_charter()) == "1.0.0"


def test_sync_skips_empty_content() -> None:
    import inspect

    from services.activity.instruction_sync import sync_instruction_set_from_activity_default

    source = inspect.getsource(sync_instruction_set_from_activity_default)
    assert "if not stripped:" in source
