"""RAG retrieval with server-side collection scope and pgvector search."""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.logging import get_logger
from models.kb import (
    DocumentChunk,
    KBDocument,
    KBDocumentStatus,
    KBCollection,
    KBCollectionAttachment,
    TaskDocument,
    ThreadDocument,
    ThreadDocumentLoadStrategy,
)
from models.task import Task
from models.thread import Thread
from services.document.embedder import DocumentEmbedder

logger = get_logger(__name__)

ENTITY_TYPE_TASK = "task"
ENTITY_TYPE_CLUSTER = "cluster"
FALLBACK_THRESHOLD = 0.5
MIN_RESULTS_BEFORE_FALLBACK = 3


class RAGScopeError(Exception):
    """Raised when task/thread scope cannot be resolved."""


@dataclass
class CollectionScope:
    """KB collection scope with priority levels for retrieval."""

    ordered_ids: list[UUID]
    priority_by_id: dict[UUID, int]


@dataclass
class ScoredChunk:
    """Document chunk with similarity score and priority level."""

    chunk: DocumentChunk
    similarity: float
    priority_level: int


@dataclass
class ContextChunk:
    """Chunk prepared for context assembly with source metadata."""

    chunk: DocumentChunk
    similarity: float
    priority_level: int
    source_metadata: dict[str, Any] = field(default_factory=lambda: dict[str, Any]())


class RAGRetriever:
    """Retrieve document chunks for RAG using org isolation and priority scope."""

    def __init__(self, embedder: DocumentEmbedder | None = None) -> None:
        self._embedder = embedder or DocumentEmbedder()

    async def get_allowed_collection_ids(
        self,
        task_id: UUID,
        thread_id: UUID,
        session: AsyncSession,
    ) -> list[UUID]:
        """Compute allowed KB collection IDs in priority order (server-side only).

        Priority for collections: task attachments → cluster attachments → org collection.

        Thread-scoped documents are not collections; they are handled in ``retrieve``.

        Args:
            task_id: Task UUID.
            thread_id: Thread UUID (validated against the task).
            session: Async database session.

        Returns:
            Deduplicated collection UUIDs in priority order.

        Raises:
            RAGScopeError: If the task or thread cannot be resolved.
        """
        task, _thread = await self._load_task_and_thread(task_id, thread_id, session)
        scope = await self._resolve_collection_scope(task, session)
        allowed = scope.ordered_ids
        logger.info(
            "rag_allowed_collections_computed",
            task_id=str(task_id),
            thread_id=str(thread_id),
            org_id=str(task.org_id),
            collection_count=len(allowed),
        )
        return allowed

    async def retrieve(
        self,
        query: str,
        task_id: UUID,
        thread_id: UUID,
        session: AsyncSession,
        top_k: int = 10,
        threshold: float = 0.7,
    ) -> list[DocumentChunk]:
        """Embed the query and retrieve relevant chunks within allowed scope.

        Args:
            query: Natural language query text.
            task_id: Task UUID.
            thread_id: Thread UUID.
            session: Async database session.
            top_k: Maximum chunks to return.
            threshold: Minimum cosine similarity (0–1).

        Returns:
            Document chunks ranked by descending similarity.
        """
        started = time.perf_counter()
        query_hash = _hash_query(query)

        task, thread = await self._load_task_and_thread(task_id, thread_id, session)
        scored, threshold_used = await self._retrieve_scored(
            query=query,
            task=task,
            thread=thread,
            session=session,
            top_k=top_k,
            threshold=threshold,
        )
        chunks = [item.chunk for item in scored]
        latency_ms = int((time.perf_counter() - started) * 1000)

        logger.info(
            "rag_retrieval",
            query_hash=query_hash,
            chunks_retrieved=len(chunks),
            threshold_used=threshold_used,
            latency_ms=latency_ms,
            task_id=str(task_id),
            thread_id=str(thread_id),
        )
        return chunks

    async def retrieve_for_context(
        self,
        query: str,
        task_id: UUID,
        thread_id: UUID,
        session: AsyncSession,
        top_k: int = 10,
        threshold: float = 0.7,
    ) -> list[ContextChunk]:
        """Retrieve chunks and attach source document metadata for context assembly."""
        started = time.perf_counter()
        query_hash = _hash_query(query)

        task, thread = await self._load_task_and_thread(task_id, thread_id, session)
        scored, threshold_used = await self._retrieve_scored(
            query=query,
            task=task,
            thread=thread,
            session=session,
            top_k=top_k,
            threshold=threshold,
        )
        context_chunks = await self._attach_source_metadata(session, scored)
        latency_ms = int((time.perf_counter() - started) * 1000)

        logger.info(
            "rag_retrieval",
            query_hash=query_hash,
            chunks_retrieved=len(context_chunks),
            threshold_used=threshold_used,
            latency_ms=latency_ms,
            task_id=str(task_id),
            thread_id=str(thread_id),
            for_context=True,
        )
        return context_chunks

    async def _retrieve_scored(
        self,
        *,
        query: str,
        task: Task,
        thread: Thread,
        session: AsyncSession,
        top_k: int,
        threshold: float,
    ) -> tuple[list[ScoredChunk], float]:
        """Run embedding, scoped vector search, and optional threshold fallback."""
        scope = await self._resolve_collection_scope(task, session)
        thread_document_ids = await self._rag_task_document_ids(session, task_id=task.id)

        if not scope.ordered_ids and not thread_document_ids:
            return [], threshold

        query_embedding = await asyncio.to_thread(self._embedder.embed, [query])
        if not query_embedding:
            return [], threshold

        vector = query_embedding[0]
        threshold_used = threshold
        scored = await self._vector_search(
            session,
            org_id=task.org_id,
            query_embedding=vector,
            allowed_collection_ids=scope.ordered_ids,
            collection_priority=scope.priority_by_id,
            thread_document_ids=thread_document_ids,
            top_k=top_k,
            threshold=threshold_used,
        )

        if len(scored) < MIN_RESULTS_BEFORE_FALLBACK and threshold_used > FALLBACK_THRESHOLD:
            threshold_used = FALLBACK_THRESHOLD
            scored = await self._vector_search(
                session,
                org_id=task.org_id,
                query_embedding=vector,
                allowed_collection_ids=scope.ordered_ids,
                collection_priority=scope.priority_by_id,
                thread_document_ids=thread_document_ids,
                top_k=top_k,
                threshold=threshold_used,
            )

        scored.sort(key=lambda item: item.similarity, reverse=True)
        return scored, threshold_used

    async def _resolve_collection_scope(
        self,
        task: Task,
        session: AsyncSession,
    ) -> CollectionScope:
        """Resolve KB collection IDs and per-level priority (2=task, 3=cluster, 4=org)."""
        task_collections = await self._collection_ids_for_entity(
            session,
            entity_type=ENTITY_TYPE_TASK,
            entity_id=task.id,
        )
        cluster_collections: list[UUID] = []
        if task.cluster_id is not None:
            cluster_collections = await self._collection_ids_for_entity(
                session,
                entity_type=ENTITY_TYPE_CLUSTER,
                entity_id=task.cluster_id,
            )
        org_collections = await self._org_collection_ids(session, org_id=task.org_id)
        priority_by_id = _collection_priority_map(
            task_collections,
            cluster_collections,
            org_collections,
        )
        ordered_ids = _dedupe_preserve_order(
            task_collections + cluster_collections + org_collections,
        )
        return CollectionScope(ordered_ids=ordered_ids, priority_by_id=priority_by_id)

    async def _load_task_and_thread(
        self,
        task_id: UUID,
        thread_id: UUID,
        session: AsyncSession,
    ) -> tuple[Task, Thread]:
        task = await session.get(Task, task_id)
        if task is None:
            raise RAGScopeError(f"Task not found: {task_id}")

        thread = await session.get(Thread, thread_id)
        if thread is None:
            raise RAGScopeError(f"Thread not found: {thread_id}")

        if thread.task_id != task.id:
            raise RAGScopeError(
                f"Thread {thread_id} does not belong to task {task_id}",
            )

        if thread.org_id != task.org_id:
            raise RAGScopeError("Thread and task org_id mismatch")

        return task, thread

    async def _collection_ids_for_entity(
        self,
        session: AsyncSession,
        *,
        entity_type: str,
        entity_id: UUID,
    ) -> list[UUID]:
        result = await session.execute(
            select(KBCollectionAttachment.collection_id)
            .where(
                KBCollectionAttachment.entity_type == entity_type,
                KBCollectionAttachment.entity_id == entity_id,
            )
            .order_by(KBCollectionAttachment.attached_at.asc()),
        )
        return list(result.scalars().all())

    async def _org_collection_ids(self, session: AsyncSession, *, org_id: UUID) -> list[UUID]:
        result = await session.execute(
            select(KBCollection.id)
            .where(
                KBCollection.org_id == org_id,
                KBCollection.is_org_collection.is_(True),
            )
            .order_by(KBCollection.created_at.asc()),
        )
        return list(result.scalars().all())

    async def _rag_task_document_ids(
        self,
        session: AsyncSession,
        *,
        task_id: UUID,
    ) -> list[UUID]:
        """Task documents eligible for RAG (indexed, RAG strategy, ready)."""
        result = await session.execute(
            select(TaskDocument.id).where(
                TaskDocument.task_id == task_id,
                TaskDocument.load_strategy == ThreadDocumentLoadStrategy.RAG,
                TaskDocument.status == KBDocumentStatus.READY,
            ),
        )
        return list(result.scalars().all())

    async def _rag_thread_document_ids(
        self,
        session: AsyncSession,
        *,
        thread_id: UUID,
    ) -> list[UUID]:
        """Legacy thread documents eligible for RAG (deprecated)."""
        result = await session.execute(
            select(ThreadDocument.id).where(
                ThreadDocument.thread_id == thread_id,
                ThreadDocument.load_strategy == ThreadDocumentLoadStrategy.RAG,
                ThreadDocument.status == KBDocumentStatus.READY,
            ),
        )
        return list(result.scalars().all())

    async def _vector_search(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        query_embedding: list[float],
        allowed_collection_ids: list[UUID],
        collection_priority: dict[UUID, int],
        thread_document_ids: list[UUID],
        top_k: int,
        threshold: float,
    ) -> list[ScoredChunk]:
        scope_filters = _build_scope_filters(
            allowed_collection_ids=allowed_collection_ids,
            thread_document_ids=thread_document_ids,
        )
        if scope_filters is None:
            return []

        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        similarity = (1 - distance).label("similarity")

        kb_ready = and_(
            DocumentChunk.document_id.is_not(None),
            KBDocument.is_active.is_(True),
            KBDocument.is_deleted.is_(False),
            KBDocument.status == KBDocumentStatus.READY,
        )
        chunk_visible = or_(
            DocumentChunk.task_document_id.in_(thread_document_ids),
            DocumentChunk.thread_document_id.in_(thread_document_ids),
            kb_ready,
        )

        stmt = (
            select(DocumentChunk, similarity)
            .outerjoin(KBDocument, DocumentChunk.document_id == KBDocument.id)
            .where(
                DocumentChunk.org_id == org_id,
                scope_filters,
                chunk_visible,
                similarity >= threshold,
            )
            .order_by(distance.asc())
            .limit(top_k)
        )

        result = await session.execute(stmt)
        scored: list[ScoredChunk] = []

        for chunk, sim in result.all():
            priority = _priority_level_for_chunk(
                chunk,
                thread_document_ids=thread_document_ids,
                collection_priority=collection_priority,
            )
            scored.append(
                ScoredChunk(
                    chunk=chunk,
                    similarity=float(sim),
                    priority_level=priority,
                ),
            )

        return scored

    async def _attach_source_metadata(
        self,
        session: AsyncSession,
        scored_chunks: list[ScoredChunk],
    ) -> list[ContextChunk]:
        if not scored_chunks:
            return []

        kb_doc_ids = {
            chunk.chunk.document_id
            for chunk in scored_chunks
            if chunk.chunk.document_id is not None
        }
        thread_doc_ids = {
            chunk.chunk.thread_document_id
            for chunk in scored_chunks
            if chunk.chunk.thread_document_id is not None
        }
        task_doc_ids = {
            chunk.chunk.task_document_id
            for chunk in scored_chunks
            if chunk.chunk.task_document_id is not None
        }

        kb_docs: dict[UUID, KBDocument] = {}
        if kb_doc_ids:
            kb_result = await session.execute(
                select(KBDocument)
                .where(KBDocument.id.in_(kb_doc_ids))
                .options(selectinload(KBDocument.collection)),
            )
            kb_docs = {doc.id: doc for doc in kb_result.scalars().all()}

        thread_docs: dict[UUID, ThreadDocument] = {}
        if thread_doc_ids:
            thread_result = await session.execute(
                select(ThreadDocument).where(ThreadDocument.id.in_(thread_doc_ids)),
            )
            thread_docs = {doc.id: doc for doc in thread_result.scalars().all()}

        task_docs: dict[UUID, TaskDocument] = {}
        if task_doc_ids:
            task_result = await session.execute(
                select(TaskDocument).where(TaskDocument.id.in_(task_doc_ids)),
            )
            task_docs = {doc.id: doc for doc in task_result.scalars().all()}

        context_chunks: list[ContextChunk] = []
        for scored in scored_chunks:
            source_metadata = _source_metadata_for_chunk(
                scored.chunk,
                kb_documents=kb_docs,
                thread_documents=thread_docs,
                task_documents=task_docs,
            )
            context_chunks.append(
                ContextChunk(
                    chunk=scored.chunk,
                    similarity=scored.similarity,
                    priority_level=scored.priority_level,
                    source_metadata=source_metadata,
                ),
            )

        return context_chunks


def _build_scope_filters(
    *,
    allowed_collection_ids: list[UUID],
    thread_document_ids: list[UUID],
) -> Any | None:
    """Build OR filter for task documents and allowed KB collections."""
    clauses: list[Any] = []
    if thread_document_ids:
        clauses.append(DocumentChunk.task_document_id.in_(thread_document_ids))
        clauses.append(DocumentChunk.thread_document_id.in_(thread_document_ids))
    if allowed_collection_ids:
        clauses.append(DocumentChunk.collection_id.in_(allowed_collection_ids))
    if not clauses:
        return None
    return or_(*clauses)


def _priority_level_for_chunk(
    chunk: DocumentChunk,
    *,
    thread_document_ids: list[UUID],
    collection_priority: dict[UUID, int],
) -> int:
    """Map chunk to priority level 1–4 (task paper → task → cluster → org collections)."""
    if (
        chunk.task_document_id is not None
        and chunk.task_document_id in thread_document_ids
    ):
        return 1
    if (
        chunk.thread_document_id is not None
        and chunk.thread_document_id in thread_document_ids
    ):
        return 1
    if chunk.collection_id is not None and chunk.collection_id in collection_priority:
        return collection_priority[chunk.collection_id]
    return 4


def _source_metadata_for_chunk(
    chunk: DocumentChunk,
    *,
    kb_documents: dict[UUID, KBDocument],
    thread_documents: dict[UUID, ThreadDocument],
    task_documents: dict[UUID, TaskDocument],
) -> dict[str, Any]:
    """Build source document metadata for context assembly."""
    base: dict[str, Any] = {
        "chunk_id": str(chunk.id),
        "chunk_index": chunk.chunk_index,
        "collection_id": str(chunk.collection_id) if chunk.collection_id else None,
    }

    if chunk.document_id is not None:
        kb_doc = kb_documents.get(chunk.document_id)
        if kb_doc is not None:
            base.update(
                {
                    "source_type": "kb_document",
                    "document_id": str(kb_doc.id),
                    "filename": kb_doc.filename,
                    "file_type": kb_doc.file_type,
                    "s3_key": kb_doc.s3_key,
                    "collection_id": str(kb_doc.collection_id),
                    "collection_name": kb_doc.collection.name if kb_doc.collection else None,
                },
            )
            return base

    if chunk.task_document_id is not None:
        task_doc = task_documents.get(chunk.task_document_id)
        if task_doc is not None:
            base.update(
                {
                    "source_type": "task_document",
                    "task_document_id": str(task_doc.id),
                    "filename": task_doc.filename,
                    "file_type": task_doc.file_type,
                    "s3_key": task_doc.s3_key,
                    "load_strategy": task_doc.load_strategy.value,
                },
            )
            return base

    if chunk.thread_document_id is not None:
        thread_doc = thread_documents.get(chunk.thread_document_id)
        if thread_doc is not None:
            base.update(
                {
                    "source_type": "thread_document",
                    "thread_document_id": str(thread_doc.id),
                    "filename": thread_doc.filename,
                    "file_type": thread_doc.file_type,
                    "s3_key": thread_doc.s3_key,
                    "load_strategy": thread_doc.load_strategy.value,
                },
            )
            return base

    base["source_type"] = "unknown"
    return base


def _collection_priority_map(
    task_collections: list[UUID],
    cluster_collections: list[UUID],
    org_collections: list[UUID],
) -> dict[UUID, int]:
    """Assign priority 2 (task), 3 (cluster), 4 (org); first attachment wins on overlap."""
    priority: dict[UUID, int] = {}
    for collection_id in task_collections:
        priority.setdefault(collection_id, 2)
    for collection_id in cluster_collections:
        priority.setdefault(collection_id, 3)
    for collection_id in org_collections:
        priority.setdefault(collection_id, 4)
    return priority


def _dedupe_preserve_order(items: list[UUID]) -> list[UUID]:
    return list(dict.fromkeys(items))


def _hash_query(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
