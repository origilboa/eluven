"""Admin ActivityLibrary API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AdminActivityPromptResponse(BaseModel):
    """Activity prompt on an activity type."""

    id: UUID
    prompt_text: str
    stage: str
    sequence_index: int

    model_config = {"from_attributes": True}


class AdminActivityLibraryEntryResponse(BaseModel):
    """Full activity type for admin management."""

    id: UUID
    thread_type: str
    module_type: str
    display_name: str
    description: str | None
    scope: str
    is_active: bool
    default_model_id: str
    fallback_model_id: str | None
    token_budget: int | None
    token_budget_warning_threshold: float
    supports_automation: bool
    default_instruction_content: str | None
    prompt_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminActivityLibraryDetailResponse(AdminActivityLibraryEntryResponse):
    """Activity type with activity prompts."""

    prompts: list[AdminActivityPromptResponse] = Field(default_factory=list)


class CreateActivityLibraryEntryRequest(BaseModel):
    """Create a platform activity type."""

    thread_type: str = Field(min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    module_type: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    default_model_id: str | None = Field(default=None, max_length=100)
    fallback_model_id: str | None = Field(default=None, max_length=100)
    token_budget: int | None = Field(default=None, ge=1000)
    token_budget_warning_threshold: float = Field(default=0.8, ge=0.1, le=1.0)
    supports_automation: bool = True
    default_instruction_content: str | None = None
    is_active: bool = True


class UpdateActivityLibraryEntryRequest(BaseModel):
    """Update an activity type."""

    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    default_model_id: str | None = Field(default=None, max_length=100)
    fallback_model_id: str | None = None
    token_budget: int | None = Field(default=None, ge=1000)
    token_budget_warning_threshold: float | None = Field(default=None, ge=0.1, le=1.0)
    supports_automation: bool | None = None
    default_instruction_content: str | None = None
    is_active: bool | None = None


class UpsertActivityPromptRequest(BaseModel):
    """Single activity prompt payload."""

    prompt_text: str = Field(min_length=1)


class ReplaceActivityPromptsRequest(BaseModel):
    """Replace all activity prompts for an activity type."""

    prompts: list[UpsertActivityPromptRequest] = Field(default_factory=list)
