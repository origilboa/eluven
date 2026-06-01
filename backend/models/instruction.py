"""Instruction layer models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, str_enum

if TYPE_CHECKING:
    from models.thread import Thread


class InstructionLevel(str, Enum):
    """Five-level instruction hierarchy."""

    PLATFORM = "platform"
    ORG = "org"
    USER = "user"
    CLUSTER = "cluster"
    TASK = "task"


class InstructionSet(Base):
    """Instruction set at one level of the hierarchy."""

    __tablename__ = "instruction_sets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    level: Mapped[InstructionLevel] = mapped_column(str_enum(InstructionLevel), nullable=False)
    thread_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    active_version_id: Mapped[UUID | None] = mapped_column(nullable=True)
    platform_id: Mapped[UUID | None] = mapped_column(nullable=True)
    owner_org_id: Mapped[UUID | None] = mapped_column(ForeignKey("orgs.id"), nullable=True)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    cluster_id: Mapped[UUID | None] = mapped_column(ForeignKey("clusters.id"), nullable=True)
    task_id: Mapped[UUID | None] = mapped_column(ForeignKey("tasks.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    versions: Mapped[list["InstructionVersion"]] = relationship(back_populates="instruction_set")


class InstructionVersion(Base):
    """Immutable version of instruction content."""

    __tablename__ = "instruction_versions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    instruction_set_id: Mapped[UUID] = mapped_column(
        ForeignKey("instruction_sets.id"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    change_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    instruction_set: Mapped[InstructionSet] = relationship(back_populates="versions")


class TaskThreadTypeInstruction(Base):
    """Task-specific addendum for a thread type (not versioned in MVP)."""

    __tablename__ = "task_thread_type_instructions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    thread_type: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )


class TaskInstructionOverride(Base):
    """Record of which instruction level was overridden for a task or thread."""

    __tablename__ = "task_instruction_overrides"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    thread_id: Mapped[UUID | None] = mapped_column(ForeignKey("threads.id"), nullable=True)
    overrides_level: Mapped[InstructionLevel] = mapped_column(
        str_enum(InstructionLevel),
        nullable=False,
    )
    override_description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    thread: Mapped[Thread | None] = relationship()
