"""Schemas for the activity type creation orchestrator stream API."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from schemas.prompt_assistant import ActivityDraftMetadata, ActivityPromptDraftItem


class ActivityAssistantStep(str, Enum):
    """Wizard steps for the orchestrator."""

    PURPOSE = "purpose"
    IDENTITY = "identity"
    MODE = "mode"
    INSTRUCTIONS = "instructions"
    PROMPTS = "prompts"
    ROUTING = "routing"
    REVIEW = "review"


class ActivityTypeDraft(BaseModel):
    """Client-held wizard draft."""

    module_type: str | None = None
    purpose_notes: str | None = None
    thread_type: str | None = None
    display_name: str | None = None
    description: str | None = None
    supports_automation: bool | None = None
    default_instruction_content: str | None = None
    prompts: list[ActivityPromptDraftItem] = Field(default_factory=list)
    default_model_id: str | None = None
    fallback_model_id: str | None = None
    token_budget: int | None = None
    token_budget_warning_threshold: float | None = None
    model_routing_rationale: str | None = None
    scope_level: Literal["platform", "org"] = "platform"


class ActivityOrchestratorChatMessage(BaseModel):
    """Ephemeral orchestrator sidebar message."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class ActivityOrchestratorStreamRequest(BaseModel):
    """Stream request for the activity type orchestrator."""

    step: ActivityAssistantStep
    draft: ActivityTypeDraft
    activity_draft: ActivityDraftMetadata | None = None
    messages: list[ActivityOrchestratorChatMessage] = Field(default_factory=list)
    locale: Literal["en", "he"] = "en"
