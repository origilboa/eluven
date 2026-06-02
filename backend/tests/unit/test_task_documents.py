"""Unit tests for task document processing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from models.kb import KBDocumentStatus, TaskDocument, ThreadDocumentLoadStrategy
from models.task import Task
from services.document.processor import DocumentNotFoundError, DocumentProcessor


@pytest.mark.asyncio
async def test_process_task_document_full_text() -> None:
    """Small task documents use full-text strategy without chunking."""
    task_id = uuid4()
    document_id = uuid4()
    org_id = uuid4()

    task_document = TaskDocument(
        id=document_id,
        task_id=task_id,
        filename="paper.txt",
        s3_key=f"{org_id}/tasks/{task_id}/{document_id}/paper.txt",
        size_bytes=100,
        file_type="txt",
        load_strategy=ThreadDocumentLoadStrategy.FULL_TEXT,
        status=KBDocumentStatus.PENDING,
        uploaded_by=uuid4(),
    )
    task = Task(
        id=task_id,
        org_id=org_id,
        owner_id=uuid4(),
        title="Review task",
        module_type="external_paper_review",
    )

    session = AsyncMock()

    async def get_model(model: type, pk: object) -> TaskDocument | Task | None:
        if pk == document_id:
            return task_document
        if pk == task_id:
            return task
        return None

    session.get = AsyncMock(side_effect=get_model)
    session.flush = AsyncMock()
    session.execute = AsyncMock()

    storage = MagicMock()
    storage.download_file.return_value = b"Short paper text."

    extractor = MagicMock()
    extracted = MagicMock()
    extracted.text = "Short paper text."
    extracted.metadata = {}
    extracted.tables = []
    extractor.extract.return_value = extracted

    chunker = MagicMock()
    chunker.count_tokens.return_value = 100

    processor = DocumentProcessor(storage=storage, extractor=extractor, chunker=chunker)
    processor._full_text_threshold = 4000

    await processor.process_task_document(document_id, session)

    assert task_document.status == KBDocumentStatus.READY
    assert task_document.load_strategy == ThreadDocumentLoadStrategy.FULL_TEXT
    assert task_document.token_count == 100


@pytest.mark.asyncio
async def test_process_task_document_not_found() -> None:
    """Missing task document raises DocumentNotFoundError."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)

    processor = DocumentProcessor()
    with pytest.raises(DocumentNotFoundError):
        await processor.process_task_document(uuid4(), session)
