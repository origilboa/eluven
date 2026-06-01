"""TaskMemoryEntry model."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, str_enum

if TYPE_CHECKING:
    from models.task import Task
    from models.thread import Thread


class TaskMemoryEntryType(str, Enum):
    """Closed set of task memory entry categories."""

    FINDING = "finding"
    ASSUMPTION = "assumption"
    GAP = "gap"
    REFERENCE = "reference"


class TaskMemoryEntry(Base):
    """Persistent structured finding accumulated across threads in a Task."""

    __tablename__ = "task_memory_entries"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    thread_id: Mapped[UUID] = mapped_column(ForeignKey("threads.id"), nullable=False)
    entry_type: Mapped[TaskMemoryEntryType] = mapped_column(
        str_enum(TaskMemoryEntryType),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_chunk_ids: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    instruction_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_automated: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    task: Mapped[Task] = relationship(back_populates="memory_entries")
    thread: Mapped[Thread] = relationship()
