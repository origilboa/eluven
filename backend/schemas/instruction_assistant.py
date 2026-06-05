"""Schemas for the instruction authoring assistant stream API."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


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


class InstructionAssistantStreamRequest(BaseModel):
    """Stream request for the instruction authoring assistant."""

    scope: InstructionAssistantScope
    draft_content: str = ""
    messages: list[AuthoringChatMessage] = Field(default_factory=list)
    locale: Literal["en", "he"] = "en"
    integrity_review: bool = False
