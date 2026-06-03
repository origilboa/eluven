"""Task API schemas (data model Section 10.2)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CreateTaskRequest(BaseModel):
    """Request body for creating a Task."""

    title: str = Field(min_length=1, max_length=255)
    module_type: str = Field(min_length=1, max_length=100)
    cluster_id: UUID | None = None
    working_language: str | None = Field(default=None, max_length=10)
    context: dict[str, Any] | None = None
    structured_tags: dict[str, Any] | None = None
    freeform_tags: list[str] | None = None


class UpdateTaskRequest(BaseModel):
    """Request body for updating a Task."""

    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    cluster_id: UUID | None = None
    working_language: str | None = Field(default=None, max_length=10)
    context: dict[str, Any] | None = None
    structured_tags: dict[str, Any] | None = None
    freeform_tags: list[str] | None = None


class TaskResponse(BaseModel):
    """Task summary for list and detail responses."""

    id: UUID
    title: str
    module_type: str
    status: str
    cluster_id: UUID | None
    working_language: str | None
    context: dict[str, Any] | None
    structured_tags: dict[str, Any] | None
    freeform_tags: list[str] | None
    thread_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskMemoryEntryResponse(BaseModel):
    """Single task memory entry."""

    id: UUID
    entry_type: str
    content: str
    confidence: float | None
    thread_id: UUID
    model_id: str | None
    is_automated: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskMemoryResponse(BaseModel):
    """Task memory entries grouped by type."""

    findings: list[TaskMemoryEntryResponse]
    assumptions: list[TaskMemoryEntryResponse]
    gaps: list[TaskMemoryEntryResponse]
    references: list[TaskMemoryEntryResponse]
