"""Task and TaskTemplate models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, str_enum

if TYPE_CHECKING:
    from models.cluster import Cluster
    from models.kb import TaskDocument
    from models.memory import TaskMemoryEntry
    from models.thread import Thread
    from models.user import User


class TaskStatus(str, Enum):
    """Closed set of task lifecycle states."""

    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETE = "complete"
    ARCHIVED = "archived"


class Task(Base):
    """Primary unit of work — container for documents, threads, memory, context."""

    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    cluster_id: Mapped[UUID | None] = mapped_column(ForeignKey("clusters.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    module_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(str_enum(TaskStatus), default=TaskStatus.DRAFT)
    working_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    structured_tags: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    freeform_tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    owner: Mapped[User] = relationship(back_populates="tasks")
    cluster: Mapped[Cluster | None] = relationship(back_populates="tasks")
    threads: Mapped[list[Thread]] = relationship(back_populates="task")
    documents: Mapped[list[TaskDocument]] = relationship(back_populates="task")
    memory_entries: Mapped[list[TaskMemoryEntry]] = relationship(back_populates="task")


class TaskTemplate(Base):
    """Reusable task configuration template (schema only in MVP)."""

    __tablename__ = "task_templates"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    module_type: Mapped[str] = mapped_column(String(100), nullable=False)
    working_language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    default_thread_types: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    default_collection_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        default=list,
    )
    context_defaults: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )
