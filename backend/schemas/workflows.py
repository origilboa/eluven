"""Workflow API schemas (data model Section 10.6)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class WorkflowTemplateResponse(BaseModel):
    """Workflow template available for execution."""

    id: UUID
    name: str
    description: str | None
    module_type: str
    scope: str
    thread_sequence: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class StartWorkflowRequest(BaseModel):
    """Request body to start a workflow on a task."""

    template_id: UUID


class WorkflowThreadExecutionResponse(BaseModel):
    """Status of a single step in a workflow execution."""

    id: UUID
    thread_type: str
    sequence_index: int
    status: str
    thread_id: UUID | None
    retry_count: int
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class WorkflowInterventionResponse(BaseModel):
    """Paused workflow awaiting user input."""

    id: UUID
    workflow_thread_execution_id: UUID
    trigger_type: str
    question: str
    user_response: str | None
    triggered_at: datetime
    responded_at: datetime | None

    model_config = {"from_attributes": True}


class WorkflowExecutionResponse(BaseModel):
    """Workflow execution status with thread steps and interventions."""

    id: UUID
    task_id: UUID
    status: str
    current_thread_index: int
    total_threads: int
    total_tokens_used: int
    thread_executions: list[WorkflowThreadExecutionResponse]
    interventions: list[WorkflowInterventionResponse]
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class InterventionResponseRequest(BaseModel):
    """User response to a workflow intervention."""

    response: str = Field(min_length=1)
