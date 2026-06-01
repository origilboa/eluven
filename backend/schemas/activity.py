"""ActivityLibrary API schemas (data model Section 10.8)."""

from uuid import UUID

from pydantic import BaseModel


class ActivityLibraryEntryResponse(BaseModel):
    """Thread type definition from ActivityLibrary."""

    id: UUID
    thread_type: str
    module_type: str
    display_name: str
    description: str | None
    scope: str
    default_model_id: str
    token_budget: int | None
    supports_automation: bool

    model_config = {"from_attributes": True}


class ActivityLibraryDetailResponse(ActivityLibraryEntryResponse):
    """Thread type with opening Q&A question count."""

    opening_question_count: int = 0
