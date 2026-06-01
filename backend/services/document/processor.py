"""Orchestrates document extraction, chunking, embedding, and persistence."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logging import get_logger
from models.kb import DocumentChunk, KBDocument, KBDocumentStatus, ThreadDocument, ThreadDocumentLoadStrategy
from models.thread import Thread
from services.document.chunker import DocumentChunker
from services.document.embedder import DocumentEmbedder
from services.document.extractor import DocumentExtractor
from services.storage import StorageService

logger = get_logger(__name__)


class DocumentNotFoundError(Exception):
    """Raised when a document record does not exist."""


class DocumentProcessor:
    """End-to-end document indexing pipeline."""

    def __init__(
        self,
        storage: StorageService | None = None,
        extractor: DocumentExtractor | None = None,
        chunker: DocumentChunker | None = None,
        embedder: DocumentEmbedder | None = None,
    ) -> None:
        self._storage = storage or StorageService()
        self._extractor = extractor or DocumentExtractor()
        self._chunker = chunker or DocumentChunker()
        self._embedder = embedder or DocumentEmbedder()
        self._full_text_threshold = settings.thread_document_full_text_token_threshold

    async def process_kb_document(self, document_id: UUID, session: AsyncSession) -> None:
        """Extract, chunk, embed, and persist chunks for a KB document."""
        document = await session.get(KBDocument, document_id)
        if document is None:
            raise DocumentNotFoundError(f"KBDocument not found: {document_id}")

        logger.info(
            "kb_document_process_started",
            document_id=str(document_id),
            collection_id=str(document.collection_id),
            file_type=document.file_type,
        )

        document.status = KBDocumentStatus.PROCESSING
        document.processing_error = None
        await session.flush()

        try:
            file_bytes = await asyncio.to_thread(
                self._storage.download_file,
                document.s3_key,
            )
            extracted = await asyncio.to_thread(
                self._extractor.extract,
                file_bytes,
                document.file_type,
                document.filename,
            )
            chunks_data = self._chunker.chunk(
                extracted.text,
                document_id=document.id,
                collection_id=document.collection_id,
            )
            embeddings = await asyncio.to_thread(
                self._embedder.embed,
                [chunk.content for chunk in chunks_data],
            )

            await session.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document.id),
            )

            for chunk_data, embedding in zip(chunks_data, embeddings, strict=True):
                session.add(
                    DocumentChunk(
                        org_id=document.org_id,
                        collection_id=document.collection_id,
                        document_id=document.id,
                        thread_document_id=None,
                        content=chunk_data.content,
                        embedding=embedding,
                        chunk_index=chunk_data.chunk_index,
                        token_count=chunk_data.token_count,
                        metadata_={
                            **chunk_data.metadata,
                            "extraction": extracted.metadata,
                            "tables_count": len(extracted.tables),
                        },
                    ),
                )

            document.chunk_count = len(chunks_data)
            document.status = KBDocumentStatus.READY
            document.processed_at = datetime.now(UTC)
            document.processing_error = None

            logger.info(
                "kb_document_process_complete",
                document_id=str(document_id),
                chunk_count=document.chunk_count,
            )
        except Exception as exc:
            document.status = KBDocumentStatus.FAILED
            document.processing_error = str(exc)[:2000]
            logger.exception(
                "kb_document_process_failed",
                document_id=str(document_id),
                error=str(exc),
            )
            raise

    async def process_thread_document(
        self,
        thread_document_id: UUID,
        session: AsyncSession,
    ) -> None:
        """Process a thread document using full-text or RAG strategy."""
        thread_document = await session.get(ThreadDocument, thread_document_id)
        if thread_document is None:
            raise DocumentNotFoundError(f"ThreadDocument not found: {thread_document_id}")

        thread = await session.get(Thread, thread_document.thread_id)
        if thread is None:
            raise DocumentNotFoundError(f"Thread not found: {thread_document.thread_id}")

        logger.info(
            "thread_document_process_started",
            thread_document_id=str(thread_document_id),
            thread_id=str(thread_document.thread_id),
            file_type=thread_document.file_type,
        )

        thread_document.status = KBDocumentStatus.PROCESSING
        await session.flush()

        try:
            file_bytes = await asyncio.to_thread(
                self._storage.download_file,
                thread_document.s3_key,
            )
            extracted = await asyncio.to_thread(
                self._extractor.extract,
                file_bytes,
                thread_document.file_type,
                thread_document.filename,
            )
            token_count = self._chunker.count_tokens(extracted.text)
            thread_document.token_count = token_count

            if token_count <= self._full_text_threshold:
                thread_document.load_strategy = ThreadDocumentLoadStrategy.FULL_TEXT
                await session.execute(
                    delete(DocumentChunk).where(
                        DocumentChunk.thread_document_id == thread_document.id,
                    ),
                )
                thread_document.status = KBDocumentStatus.READY
                logger.info(
                    "thread_document_process_full_text",
                    thread_document_id=str(thread_document_id),
                    token_count=token_count,
                )
                return

            thread_document.load_strategy = ThreadDocumentLoadStrategy.RAG
            chunks_data = self._chunker.chunk(
                extracted.text,
                document_id=thread_document.id,
                collection_id=None,
            )
            embeddings = await asyncio.to_thread(
                self._embedder.embed,
                [chunk.content for chunk in chunks_data],
            )

            await session.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.thread_document_id == thread_document.id,
                ),
            )

            for chunk_data, embedding in zip(chunks_data, embeddings, strict=True):
                session.add(
                    DocumentChunk(
                        org_id=thread.org_id,
                        collection_id=None,
                        document_id=None,
                        thread_document_id=thread_document.id,
                        content=chunk_data.content,
                        embedding=embedding,
                        chunk_index=chunk_data.chunk_index,
                        token_count=chunk_data.token_count,
                        metadata_={
                            **chunk_data.metadata,
                            "extraction": extracted.metadata,
                            "tables_count": len(extracted.tables),
                        },
                    ),
                )

            thread_document.status = KBDocumentStatus.READY
            logger.info(
                "thread_document_process_rag_complete",
                thread_document_id=str(thread_document_id),
                token_count=token_count,
                chunk_count=len(chunks_data),
            )
        except Exception as exc:
            thread_document.status = KBDocumentStatus.FAILED
            logger.exception(
                "thread_document_process_failed",
                thread_document_id=str(thread_document_id),
                error=str(exc),
            )
            raise
