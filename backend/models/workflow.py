"""Workflow template and execution models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, str_enum


class WorkflowStatus(str, Enum):
    """Workflow execution lifecycle status."""

    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETE = "complete"


class WorkflowThreadStatus(str, Enum):
    """Individual thread step status within a workflow execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class InterventionTriggerType(str, Enum):
    """Four intervention trigger types for automated workflows."""

    MISSING_DOCUMENT = "missing_document"
    EXPLICIT_AMBIGUITY = "explicit_ambiguity"
    CONFIDENCE_BELOW_THRESHOLD = "confidence_below_threshold"
    CONFLICTING_INFORMATION = "conflicting_information"


class WorkflowTemplate(Base):
    """Reusable ordered sequence of thread types for a module."""

    __tablename__ = "workflow_templates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    module_type: Mapped[str] = mapped_column(String(100), nullable=False)
    scope: Mapped[str] = mapped_column(String(50), nullable=False)
    thread_sequence: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )


class WorkflowExecution(Base):
    """Running or completed workflow instance for a Task."""

    __tablename__ = "workflow_executions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    template_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_templates.id"),
        nullable=False,
    )
    triggered_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[WorkflowStatus] = mapped_column(
        str_enum(WorkflowStatus),
        default=WorkflowStatus.RUNNING,
    )
    current_thread_index: Mapped[int] = mapped_column(Integer, default=0)
    total_threads: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(nullable=True)


class WorkflowThreadExecution(Base):
    """Execution state for one step in a workflow sequence."""

    __tablename__ = "workflow_thread_executions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_executions.id"),
        nullable=False,
    )
    thread_id: Mapped[UUID | None] = mapped_column(ForeignKey("threads.id"), nullable=True)
    thread_type: Mapped[str] = mapped_column(String(100), nullable=False)
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[WorkflowThreadStatus] = mapped_column(
        str_enum(WorkflowThreadStatus),
        default=WorkflowThreadStatus.PENDING,
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)


class WorkflowIntervention(Base):
    """Paused workflow step awaiting user input."""

    __tablename__ = "workflow_interventions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_executions.id"),
        nullable=False,
    )
    workflow_thread_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_thread_executions.id"),
        nullable=False,
    )
    trigger_type: Mapped[InterventionTriggerType] = mapped_column(
        str_enum(InterventionTriggerType),
        nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    user_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    triggered_at: Mapped[datetime] = mapped_column(server_default=func.now())
    responded_at: Mapped[datetime | None] = mapped_column(nullable=True)
