"""Cluster API schemas (data model Section 10.3)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CreateClusterRequest(BaseModel):
    """Request body for creating a Cluster."""

    name: str = Field(min_length=1, max_length=255)
    cluster_type: str = Field(min_length=1, max_length=100)
    description: str | None = None
    working_language: str | None = Field(default=None, max_length=10)
    structured_tags: dict[str, Any] | None = None
    freeform_tags: list[str] | None = None


class UpdateClusterRequest(BaseModel):
    """Request body for updating a Cluster."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    working_language: str | None = Field(default=None, max_length=10)
    structured_tags: dict[str, Any] | None = None
    freeform_tags: list[str] | None = None


class ClusterResponse(BaseModel):
    """Cluster summary for list and detail responses."""

    id: UUID
    name: str
    cluster_type: str
    description: str | None
    working_language: str | None
    structured_tags: dict[str, Any] | None
    freeform_tags: list[str] | None
    task_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateSubmissionRequest(BaseModel):
    """Request body for creating a Submission Task under an Assignment Cluster."""

    title: str = Field(min_length=1, max_length=255)
    working_language: str | None = Field(default=None, max_length=10)
    context: dict[str, Any] | None = None
    structured_tags: dict[str, Any] | None = None
    freeform_tags: list[str] | None = None
