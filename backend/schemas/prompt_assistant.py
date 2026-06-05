"""Schemas for the activity prompt authoring assistant stream API."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class PromptAuthoringMode(str, Enum):
    """Whether authoring a draft or saved entry."""

    CREATE = "create"
    EDIT = "edit"


class ActivityPromptDraftItem(BaseModel):
    """Draft prompt in the assistant request."""

    prompt_text: str = Field(min_length=1)
    stage: Literal["opening", "mid", "closing"] = "opening"
    sequence_index: int = Field(ge=0)


class ActivityDraftMetadata(BaseModel):
    """Activity metadata for create-mode authoring."""

    display_name: str | None = None
    description: str | None = None
    thread_type: str | None = None
    module_type: str | None = None
    supports_automation: bool | None = None


class PromptAssistantScope(BaseModel):
    """Identifies the activity prompts being authored."""

    authoring_mode: PromptAuthoringMode = PromptAuthoringMode.CREATE
    level: Literal["platform", "org"] = "platform"
    activity_entry_id: str | None = None
    thread_type: str | None = None
    module_type: str | None = None
    activity_draft: ActivityDraftMetadata | None = None
    supports_automation: bool | None = None
    default_instruction_content: str | None = None


class PromptAuthoringChatMessage(BaseModel):
    """Ephemeral sidebar message."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class PromptAssistantStreamRequest(BaseModel):
    """Stream request for the prompt authoring assistant."""

    scope: PromptAssistantScope
    draft_prompts: list[ActivityPromptDraftItem] = Field(default_factory=list)
    messages: list[PromptAuthoringChatMessage] = Field(default_factory=list)
    locale: Literal["en", "he"] = "en"
