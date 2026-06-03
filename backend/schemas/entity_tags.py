"""Structured and freeform entity tag schemas."""

from typing import Any

from pydantic import BaseModel, Field


class EntityTagsUpdate(BaseModel):
    """Structured and freeform tags on a Cluster or Task."""

    structured_tags: dict[str, Any] | None = None
    freeform_tags: list[str] | None = None


class SubmissionStructuredTags(BaseModel):
    """Required structured tags when creating a Submission."""

    student_name: str = Field(min_length=1, max_length=255)
