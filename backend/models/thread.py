"""Thread and ThreadMessage models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, str_enum

if TYPE_CHECKING:
    from models.kb import ThreadDocument
    from models.task import Task
    from models.user import User


class ThreadStatus(str, Enum):
    """Closed set of thread lifecycle states."""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETE = "complete"
    ARCHIVED = "archived"


class MessageRole(str, Enum):
    """Closed set of message author roles."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Thread(Base):
    """Focused AI conversation within a Task for a specific analytical activity."""

    __tablename__ = "threads"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    thread_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[ThreadStatus] = mapped_column(
        str_enum(ThreadStatus),
        default=ThreadStatus.DRAFT,
    )
    working_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_automated: Mapped[bool] = mapped_column(Boolean, default=False)
    instruction_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    token_budget: Mapped[int | None] = mapped_column(nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    task: Mapped[Task] = relationship(back_populates="threads")
    owner: Mapped[User] = relationship()
    messages: Mapped[list[ThreadMessage]] = relationship(back_populates="thread")
    documents: Mapped[list[ThreadDocument]] = relationship(back_populates="thread")


class ThreadMessage(Base):
    """Single message in a Thread conversation."""

    __tablename__ = "thread_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(ForeignKey("threads.id"), nullable=False)
    role: Mapped[MessageRole] = mapped_column(str_enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_compaction_summary: Mapped[bool] = mapped_column(Boolean, default=False)
    input_tokens: Mapped[int | None] = mapped_column(nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(nullable=True)
    cached_tokens: Mapped[int | None] = mapped_column(nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    thread: Mapped[Thread] = relationship(back_populates="messages")
