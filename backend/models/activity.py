"""ActivityLibrary and activity prompt models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, str_enum

if TYPE_CHECKING:
    from models.thread import Thread


class PromptStage(str, Enum):
    """When a prompt is surfaced during a thread (MVP shows all at start)."""

    OPENING = "opening"
    MID_THREAD = "mid"
    CLOSING = "closing"


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
    is_active: Mapped[bool] = mapped_column(default=True)
    default_model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    fallback_model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_routing_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_budget: Mapped[int | None] = mapped_column(nullable=True)
    token_budget_warning_threshold: Mapped[float] = mapped_column(Float, default=0.8)
    supports_automation: Mapped[bool] = mapped_column(default=True)
    automation_execution_spec: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    default_instruction_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    prompts: Mapped[list["ActivityPrompt"]] = relationship(back_populates="activity_entry")


class ActivityPrompt(Base):
    """Analytical prompt for an ActivityLibrary thread type."""

    __tablename__ = "activity_prompts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    activity_entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("activity_library_entries.id"),
        nullable=False,
    )
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    stage: Mapped[PromptStage] = mapped_column(str_enum(PromptStage), nullable=False)
    sequence_index: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    activity_entry: Mapped[ActivityLibraryEntry] = relationship(back_populates="prompts")


class ThreadPromptUsage(Base):
    """Tracks when a user applied an activity prompt in a manual thread."""

    __tablename__ = "thread_prompt_usage"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(ForeignKey("threads.id"), nullable=False)
    prompt_id: Mapped[UUID] = mapped_column(
        ForeignKey("activity_prompts.id"),
        nullable=False,
    )
    used_at: Mapped[datetime] = mapped_column(server_default=func.now())

    thread: Mapped[Thread] = relationship()


# Backward-compatible aliases
QAStage = PromptStage
