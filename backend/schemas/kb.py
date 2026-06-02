"""KB API schemas (data model Section 10.5)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CreateCollectionRequest(BaseModel):
    """Request body for creating a KBCollection."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class UpdateCollectionRequest(BaseModel):
    """Request body for updating a KBCollection."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class AttachCollectionRequest(BaseModel):
    """Attach a collection to a Task or Cluster."""

    entity_type: Literal["task", "cluster"]
    entity_id: UUID


class KBAttachmentResponse(BaseModel):
    """Collection attachment with resolved entity display name."""

    id: UUID
    entity_type: str
    entity_id: UUID
    entity_name: str
    attached_at: datetime

    model_config = {"from_attributes": True}


class KBDocumentResponse(BaseModel):
    """KB document summary for API responses."""

    id: UUID
    filename: str
    file_type: str
    size_bytes: int
    status: str
    chunk_count: int
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class KBCollectionResponse(BaseModel):
    """KBCollection with document count and attachments."""

    id: UUID
    name: str
    description: str | None
    document_count: int
    attachments: list[KBAttachmentResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskReferenceCollectionResponse(BaseModel):
    """KB collection linked to a task directly or via its cluster."""

    id: UUID
    attachment_id: UUID
    name: str
    description: str | None
    document_count: int
    attached_via: Literal["task", "cluster"]
    created_at: datetime
