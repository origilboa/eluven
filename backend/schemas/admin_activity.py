"""Admin ActivityLibrary API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AdminThreadQAQuestionResponse(BaseModel):
    """Q&A question on an activity type."""

    id: UUID
    question_text: str
    stage: str
    response_type: str
    options: list[str] | None
    is_required: bool
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
    opening_question_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminActivityLibraryDetailResponse(AdminActivityLibraryEntryResponse):
    """Activity type with opening Q&A questions."""

    opening_questions: list[AdminThreadQAQuestionResponse] = Field(default_factory=list)


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


class UpsertOpeningQAQuestionRequest(BaseModel):
    """Single opening Q&A question payload."""

    question_text: str = Field(min_length=1)
    is_required: bool = True
    sequence_index: int = Field(ge=0)


class ReplaceOpeningQuestionsRequest(BaseModel):
    """Replace all opening questions for an activity type."""

    questions: list[UpsertOpeningQAQuestionRequest] = Field(default_factory=list)
