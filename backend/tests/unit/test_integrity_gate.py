"""Tests for instruction integrity gate helpers."""

from __future__ import annotations

from uuid import uuid4

import pytest

from models.instruction import InstructionLevel, InstructionSet
from schemas.instruction_assistant import AuthoringTarget, InstructionAssistantScope
from services.instructions.integrity_gate import (
    compute_content_hash,
    deterministic_integrity_issues,
    issue_approval_token,
    require_instruction_integrity_approval,
    scope_key_from_assistant_scope,
    scope_key_from_instruction_set,
    verify_approval_token,
)


def test_scope_keys_match_instruction_set_and_assistant_scope() -> None:
    instruction_set = InstructionSet(
        level=InstructionLevel.PLATFORM,
        thread_type="initial_read",
        org_id=uuid4(),
    )
    scope = InstructionAssistantScope(
        authoring_target=AuthoringTarget.INSTRUCTION_SET,
        level="platform",
        thread_type="initial_read",
    )
    assert scope_key_from_instruction_set(instruction_set) == scope_key_from_assistant_scope(
        scope,
    )


def test_deterministic_issues_flag_model_ids() -> None:
    issues = deterministic_integrity_issues(
        "Use us.anthropic.claude-sonnet for all replies.",
    )
    assert len(issues) == 1
    assert issues[0]["code"] == "wrong_bucket"
    assert issues[0]["severity"] == "blocking"


def test_approval_token_round_trip() -> None:
    user_id = str(uuid4())
    scope_key = "instruction_set|platform|initial_read|||||"
    content = "Review papers rigorously."
    content_hash = compute_content_hash(content)
    token, expires_at = issue_approval_token(
        user_id=user_id,
        scope_key=scope_key,
        content_hash=content_hash,
    )
    assert expires_at > 0
    assert verify_approval_token(
        user_id=user_id,
        scope_key=scope_key,
        content_hash=content_hash,
        token=token,
    )


def test_require_instruction_integrity_approval_rejects_missing_token() -> None:
    with pytest.raises(Exception) as exc_info:
        require_instruction_integrity_approval(
            user_id=str(uuid4()),
            scope_key="instruction_set|platform||||||",
            content="Draft",
            token=None,
        )
    assert exc_info.value.status_code == 400  # type: ignore[attr-defined]
