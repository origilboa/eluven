"""Thread API schemas (data model Section 10.4)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from schemas.tasks import TaskMemoryEntryResponse


class CreateThreadRequest(BaseModel):
    """Request body for creating a Thread."""

    thread_type: str = Field(min_length=1, max_length=100)
    title: str | None = Field(default=None, max_length=255)
    working_language: str | None = Field(default=None, max_length=10)


class UpdateThreadRequest(BaseModel):
    """Request body for updating a Thread."""

    title: str = Field(min_length=1, max_length=255)


class ThreadResponse(BaseModel):
    """Thread summary for list and detail responses."""

    id: UUID
    task_id: UUID
    title: str
    thread_type: str
    status: str
    working_language: str | None
    is_automated: bool
    token_budget: int | None
    tokens_used: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    """Save a user message without triggering AI."""

    content: str = Field(min_length=1)


class StreamRequest(BaseModel):
    """Request body for SSE AI streaming."""

    content: str = Field(min_length=1)


class MessageResponse(BaseModel):
    """Thread message in conversation history."""

    id: UUID
    role: str
    content: str
    is_compaction_summary: bool
    input_tokens: int | None
    output_tokens: int | None
    cached_tokens: int | None
    model_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ThreadDocumentResponse(BaseModel):
    """Thread-attached document summary."""

    id: UUID
    filename: str
    file_type: str
    size_bytes: int
    status: str
    load_strategy: str
    token_count: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskDocumentResponse(BaseModel):
    """Task-attached document summary (paper under review)."""

    id: UUID
    filename: str
    file_type: str
    size_bytes: int
    status: str
    load_strategy: str
    token_count: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskThreadDocumentResponse(ThreadDocumentResponse):
    """Thread document with parent thread metadata for task-level listings."""

    thread_id: UUID
    thread_title: str
    thread_type: str


class DocumentDownloadUrlResponse(BaseModel):
    """Presigned URL for downloading a stored document."""

    url: str
    filename: str
    expires_in_seconds: int


class QAQuestionResponse(BaseModel):
    """Q&A question from ActivityLibrary with optional existing response."""

    id: UUID
    question_text: str
    stage: str
    response_type: str
    options: list[str] | None
    is_required: bool
    sequence_index: int
    response_text: str | None = None
    response_options: list[str] | None = None
    responded_at: datetime | None = None


class QAResponseRequest(BaseModel):
    """Single Q&A answer submission."""

    question_id: UUID
    response_text: str | None = None
    response_options: list[str] | None = None


class SubmitQARequest(BaseModel):
    """Batch Q&A response submission."""

    responses: list[QAResponseRequest]


class StreamStatusEvent(BaseModel):
    """SSE status event."""

    type: str = "status"
    message: str


class StreamTextEvent(BaseModel):
    """SSE text delta event."""

    type: str = "text"
    text: str


class StreamMemoryEntryEvent(BaseModel):
    """SSE task memory entry event."""

    type: str = "memory_entry"
    entry: TaskMemoryEntryResponse


class StreamDoneEvent(BaseModel):
    """SSE completion event."""

    type: str = "done"
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0
    model_id: str | None = None


class StreamErrorEvent(BaseModel):
    """SSE error event."""

    type: str = "error"
    message: str
