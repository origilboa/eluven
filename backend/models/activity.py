"""ActivityLibrary and thread Q&A models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, str_enum

if TYPE_CHECKING:
    from models.thread import Thread


class QAStage(str, Enum):
    """When a Q&A question is presented during a thread."""

    OPENING = "opening"
    MID_THREAD = "mid"
    CLOSING = "closing"


class QAResponseType(str, Enum):
    """Expected response format for a Q&A question."""

    TEXT = "text"
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"


class ActivityLibraryEntry(Base):
    """Platform thread type definition with routing and automation spec."""

    __tablename__ = "activity_library_entries"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    thread_type: Mapped[str] = mapped_column(String(100), nullable=False)
    module_type: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    default_model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    fallback_model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_routing_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_budget: Mapped[int | None] = mapped_column(nullable=True)
    token_budget_warning_threshold: Mapped[float] = mapped_column(Float, default=0.8)
    supports_automation: Mapped[bool] = mapped_column(Boolean, default=True)
    automation_execution_spec: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    qa_questions: Mapped[list["ThreadQAQuestion"]] = relationship(back_populates="activity_entry")


class ThreadQAQuestion(Base):
    """Predefined Q&A question for an ActivityLibrary thread type."""

    __tablename__ = "thread_qa_questions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    activity_entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("activity_library_entries.id"),
        nullable=False,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    stage: Mapped[QAStage] = mapped_column(str_enum(QAStage), nullable=False)
    response_type: Mapped[QAResponseType] = mapped_column(
        str_enum(QAResponseType),
        default=QAResponseType.TEXT,
    )
    options: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    activity_entry: Mapped[ActivityLibraryEntry] = relationship(back_populates="qa_questions")


class ThreadQAResponse(Base):
    """User response to a Q&A question within a Thread."""

    __tablename__ = "thread_qa_responses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(ForeignKey("threads.id"), nullable=False)
    question_id: Mapped[UUID] = mapped_column(
        ForeignKey("thread_qa_questions.id"),
        nullable=False,
    )
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    response_options: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    responded_at: Mapped[datetime] = mapped_column(server_default=func.now())

    thread: Mapped[Thread] = relationship()
