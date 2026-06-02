"""Instruction API schemas (data model Section 10.7)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class InstructionVersionResponse(BaseModel):
    """Single instruction version with active flag."""

    id: UUID
    version_number: int
    content: str
    change_note: str | None
    created_by: UUID
    created_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class InstructionSetResponse(BaseModel):
    """Instruction set with active version and version history."""

    id: UUID
    level: str
    thread_type: str | None = None
    cluster_id: UUID | None = None
    task_id: UUID | None = None
    active_version: InstructionVersionResponse | None
    versions: list[InstructionVersionResponse]

    model_config = {"from_attributes": True}


class TaskThreadTypeInstructionResponse(BaseModel):
    """Per-task, per-thread-type instruction addendum (not versioned in MVP)."""

    task_id: UUID
    thread_type: str
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UpsertTaskThreadTypeInstructionRequest(BaseModel):
    """Request body for task thread-type instruction addendum."""

    content: str = Field(min_length=1)


class CreateInstructionVersionRequest(BaseModel):
    """Request body for creating a new instruction version."""

    content: str = Field(min_length=1)
    change_note: str | None = Field(default=None, max_length=500)


class ActivateInstructionVersionRequest(BaseModel):
    """Request body for promoting a version to active."""

    version_id: UUID
