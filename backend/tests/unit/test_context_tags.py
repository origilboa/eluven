"""Tests for entity tag context assembly."""

from __future__ import annotations

from services.tags.context_tags import format_merged_tags_block


def test_format_merged_tags_block_empty() -> None:
    assert format_merged_tags_block() == ""


def test_format_merged_tags_block_renders_sections() -> None:
    block = format_merged_tags_block(
        assignment_tags={"course_level": "undergraduate"},
        task_tags={"student_name": "Alice Chen"},
        freeform_tags=["honors-section"],
    )
    assert "## Tags" in block
    assert "Assignment tags:" in block
    assert "course_level: undergraduate" in block
    assert "Task tags:" in block
    assert "student_name: Alice Chen" in block
    assert "Freeform tags: honors-section" in block
