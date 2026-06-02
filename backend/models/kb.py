"""Knowledge base and document chunk models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector  # pyright: ignore[reportMissingTypeStubs]
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, str_enum

if TYPE_CHECKING:
    from models.task import Task
    from models.thread import Thread


class KBDocumentStatus(str, Enum):
    """Document indexing pipeline status."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ThreadDocumentLoadStrategy(str, Enum):
    """How a thread document is loaded into context."""

    FULL_TEXT = "full_text"
    RAG = "rag"


class KBCollection(Base):
    """Named collection of KB documents."""

    __tablename__ = "kb_collections"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_org_collection: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    documents: Mapped[list["KBDocument"]] = relationship(back_populates="collection")
    attachments: Mapped[list["KBCollectionAttachment"]] = relationship(
        back_populates="collection",
    )


class KBCollectionAttachment(Base):
    """Links a KBCollection to a Task or Cluster."""

    __tablename__ = "kb_collection_attachments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    collection_id: Mapped[UUID] = mapped_column(
        ForeignKey("kb_collections.id"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(nullable=False)
    attached_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    attached_at: Mapped[datetime] = mapped_column(server_default=func.now())

    collection: Mapped[KBCollection] = relationship(back_populates="attachments")


class KBDocument(Base):
    """Document stored in a KBCollection."""

    __tablename__ = "kb_documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    collection_id: Mapped[UUID] = mapped_column(
        ForeignKey("kb_collections.id"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[KBDocumentStatus] = mapped_column(
        str_enum(KBDocumentStatus),
        default=KBDocumentStatus.PENDING,
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    previous_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("kb_documents.id"),
        nullable=True,
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )

    collection: Mapped[KBCollection] = relationship(back_populates="documents")


class TaskDocument(Base):
    """Manuscript or submission uploaded to a Task (paper under review)."""

    __tablename__ = "task_documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    token_count: Mapped[int | None] = mapped_column(nullable=True)
    load_strategy: Mapped[ThreadDocumentLoadStrategy] = mapped_column(
        str_enum(ThreadDocumentLoadStrategy),
        nullable=False,
    )
    status: Mapped[KBDocumentStatus] = mapped_column(
        str_enum(KBDocumentStatus),
        default=KBDocumentStatus.PENDING,
    )
    uploaded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    task: Mapped[Task] = relationship(back_populates="documents")


class ThreadDocument(Base):
    """Document uploaded directly to a Thread (deprecated — use TaskDocument)."""

    __tablename__ = "thread_documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(ForeignKey("threads.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    token_count: Mapped[int | None] = mapped_column(nullable=True)
    load_strategy: Mapped[ThreadDocumentLoadStrategy] = mapped_column(
        str_enum(ThreadDocumentLoadStrategy),
        nullable=False,
    )
    status: Mapped[KBDocumentStatus] = mapped_column(
        str_enum(KBDocumentStatus),
        default=KBDocumentStatus.PENDING,
    )
    uploaded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    thread: Mapped[Thread] = relationship(back_populates="documents")


class DocumentChunk(Base):
    """Indexed chunk with embedding for RAG retrieval."""

    __tablename__ = "document_chunks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    collection_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("kb_collections.id"),
        nullable=True,
    )
    document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("kb_documents.id"),
        nullable=True,
    )
    thread_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("thread_documents.id"),
        nullable=True,
    )
    task_document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("task_documents.id"),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536))
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
