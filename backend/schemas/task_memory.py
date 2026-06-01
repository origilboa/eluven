"""Pydantic schemas for AI-written task memory entries."""

from enum import Enum

from pydantic import BaseModel, Field


class TaskMemoryEntryType(str, Enum):
    """Closed set of task memory entry categories (AI output schema)."""

    FINDING = "finding"
    ASSUMPTION = "assumption"
    GAP = "gap"
    REFERENCE = "reference"


class TaskMemoryEntryPayload(BaseModel):
    """Structured task memory JSON emitted by the assistant."""

    type: TaskMemoryEntryType
    content: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_chunk_ids: list[str] = Field(default_factory=list)
    model_id: str | None = None
    instruction_version: str | None = None
