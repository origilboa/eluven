"""Schemas for the instruction authoring assistant stream API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AuthoringTarget(str, Enum):
    """What field the host form is authoring."""

    INSTRUCTION_SET = "instruction_set"
    ACTIVITY_LIBRARY_DEFAULT = "activity_library_default"


class ActivityDraftMetadata(BaseModel):
    """Optional activity metadata for future create flows."""

    display_name: str | None = None
    description: str | None = None
    thread_type: str | None = None
    module_type: str | None = None


class InstructionAssistantScope(BaseModel):
    """Identifies the instruction layer and entity being authored."""

    authoring_target: AuthoringTarget = AuthoringTarget.INSTRUCTION_SET
    level: Literal["platform", "org", "user", "cluster", "task", "thread"]
    cluster_id: str | None = None
    task_id: str | None = None
    thread_id: str | None = None
    thread_type: str | None = None
    module_type: str | None = None
    activity_entry_id: str | None = None
    activity_draft: ActivityDraftMetadata | None = None


class AuthoringChatMessage(BaseModel):
    """Ephemeral sidebar message."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class InstructionIntegrityIssue(BaseModel):
    """Single integrity finding with actionable guidance."""

    code: str
    severity: Literal["blocking", "warning"] = "blocking"
    title: str
    message: str
    excerpt: str | None = None
    conflicting_level: str | None = None
    recommendation: str
    suggested_target: str | None = None
    fix_strategy: Literal[
        "remove_excerpt",
        "move_to_layer",
        "rephrase_as_delta",
        "relocate_to_settings",
        "relocate_to_prompts",
        "ask_user",
    ] = "ask_user"
    needs_user_input: bool = False


class ClarifyingQuestion(BaseModel):
    """Question when integrity fix requires user context."""

    id: str
    prompt: str
    why_needed: str | None = None


class InstructionIntegrityCheckRequest(BaseModel):
    """Structured integrity check for gating save."""

    scope: InstructionAssistantScope
    draft_content: str = Field(min_length=1)
    locale: Literal["en", "he"] = "en"


class InstructionIntegrityCheckResponse(BaseModel):
    """Integrity check result with optional approval token."""

    status: Literal["pass", "fail"]
    summary: str
    content_hash: str
    issues: list[InstructionIntegrityIssue] = Field(default_factory=list)
    clarifying_questions: list[ClarifyingQuestion] = Field(default_factory=list)
    approval_token: str | None = None
    expires_at: datetime | None = None


class InstructionIntegrityRemediateRequest(BaseModel):
    """Multi-turn remediation after a failed integrity check."""

    scope: InstructionAssistantScope
    draft_content: str = Field(min_length=1)
    issues: list[InstructionIntegrityIssue] = Field(default_factory=list)
    messages: list[AuthoringChatMessage] = Field(default_factory=list)
    locale: Literal["en", "he"] = "en"


class InstructionAssistantStreamRequest(BaseModel):
    """Stream request for the instruction authoring assistant."""

    scope: InstructionAssistantScope
    draft_content: str = ""
    messages: list[AuthoringChatMessage] = Field(default_factory=list)
    locale: Literal["en", "he"] = "en"
    integrity_review: bool = False
    completeness_review: bool = False

    @model_validator(mode="after")
    def _exclusive_review_modes(self) -> InstructionAssistantStreamRequest:
        active = sum(
            [
                self.integrity_review,
                self.completeness_review,
            ],
        )
        if active > 1:
            msg = "Only one review mode per stream request"
            raise ValueError(msg)
        return self
