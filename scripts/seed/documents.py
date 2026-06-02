"""S3 upload and document processing helpers for demo seed."""

from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from models.kb import KBDocument, KBDocumentStatus, TaskDocument, ThreadDocumentLoadStrategy
from models.org import Org
from models.task import Task
from models.user import User
from services.document.processor import DocumentProcessor
from services.storage import StorageService

logger = get_logger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "backend" / "tests" / "fixtures"

_CONTENT_TYPES: dict[str, str] = {
    "pdf": "application/pdf",
    "txt": "text/plain",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def seed_skip_aws() -> bool:
    """When true, skip S3 upload and document processing (DB-only seed)."""
    return os.environ.get("SEED_SKIP_AWS", "").strip().lower() in ("1", "true", "yes")


def read_fixture_bytes(fixture_name: str) -> tuple[bytes, str, str]:
    """Return file bytes, file_type, and content_type for a fixture filename."""
    path = FIXTURES_DIR / fixture_name
    if not path.is_file():
        msg = f"Seed fixture not found: {path}"
        raise FileNotFoundError(msg)

    suffix = path.suffix.lstrip(".").lower()
    file_type = suffix if suffix in _CONTENT_TYPES else "txt"
    content_type = _CONTENT_TYPES.get(file_type, "application/octet-stream")
    return path.read_bytes(), file_type, content_type


def purge_dev_org_s3_prefix(org_id: UUID) -> None:
    """Delete all objects under the dev org prefix in the documents bucket."""
    if seed_skip_aws():
        logger.warning("seed_s3_purge_skipped", reason="SEED_SKIP_AWS")
        return

    prefix = f"{org_id}/"
    storage = StorageService()
    client = storage._client  # noqa: SLF001 — seed utility
    bucket = storage._bucket  # noqa: SLF001
    deleted = 0
    try:
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            contents = page.get("Contents") or []
            if not contents:
                continue
            keys = [{"Key": item["Key"]} for item in contents]
            client.delete_objects(Bucket=bucket, Delete={"Objects": keys})
            deleted += len(keys)
    except Exception as exc:
        logger.warning(
            "seed_s3_purge_failed",
            org_id=str(org_id),
            prefix=prefix,
            error=str(exc),
        )
        return

    logger.info("seed_s3_purge_complete", org_id=str(org_id), deleted_objects=deleted)


async def seed_task_document(
    session: AsyncSession,
    *,
    org: Org,
    task: Task,
    owner: User,
    filename: str,
    fixture_name: str,
) -> bool:
    """Upload and process a task document if missing. Returns True if created."""
    result = await session.execute(
        select(TaskDocument.id).where(
            TaskDocument.task_id == task.id,
            TaskDocument.filename == filename,
        ),
    )
    if result.scalar_one_or_none() is not None:
        return False

    file_bytes, file_type, content_type = read_fixture_bytes(fixture_name)
    document_id = uuid4()
    s3_key = f"{org.id}/tasks/{task.id}/{document_id}/{filename}"

    document = TaskDocument(
        id=document_id,
        task_id=task.id,
        filename=filename,
        s3_key=s3_key,
        size_bytes=len(file_bytes),
        file_type=file_type,
        load_strategy=ThreadDocumentLoadStrategy.FULL_TEXT,
        status=KBDocumentStatus.PENDING,
        uploaded_by=owner.id,
    )
    session.add(document)
    await session.flush()

    if seed_skip_aws():
        logger.warning(
            "seed_task_document_skipped_processing",
            task_id=str(task.id),
            filename=filename,
            reason="SEED_SKIP_AWS",
        )
        return True

    storage = StorageService()
    storage.upload_file(file_bytes, s3_key, content_type)

    processor = DocumentProcessor(storage=storage)
    try:
        await processor.process_task_document(document.id, session)
    except Exception as exc:
        document.status = KBDocumentStatus.FAILED
        await session.flush()
        logger.warning(
            "seed_task_document_process_failed",
            task_id=str(task.id),
            document_id=str(document.id),
            error=str(exc),
        )
        return True

    logger.info(
        "seed_task_document_created",
        task_id=str(task.id),
        document_id=str(document.id),
        status=document.status.value,
    )
    return True


async def seed_kb_document_processed(
    session: AsyncSession,
    *,
    org: Org,
    collection_id: UUID,
    owner: User,
    filename: str,
    fixture_name: str,
) -> KBDocument | None:
    """Upload and process a KB document if missing."""
    result = await session.execute(
        select(KBDocument).where(
            KBDocument.collection_id == collection_id,
            KBDocument.filename == filename,
        ),
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    file_bytes, file_type, content_type = read_fixture_bytes(fixture_name)
    document_id = uuid4()
    s3_key = f"{org.id}/kb/{collection_id}/{document_id}/{filename}"

    document = KBDocument(
        id=document_id,
        org_id=org.id,
        collection_id=collection_id,
        filename=filename,
        s3_key=s3_key,
        size_bytes=len(file_bytes),
        file_type=file_type,
        status=KBDocumentStatus.PENDING,
        uploaded_by=owner.id,
    )
    session.add(document)
    await session.flush()

    if seed_skip_aws():
        logger.warning(
            "seed_kb_document_skipped_processing",
            collection_id=str(collection_id),
            filename=filename,
            reason="SEED_SKIP_AWS",
        )
        return document

    storage = StorageService()
    storage.upload_file(file_bytes, s3_key, content_type)

    processor = DocumentProcessor(storage=storage)
    try:
        await processor.process_kb_document(document.id, session)
    except Exception as exc:
        document.status = KBDocumentStatus.FAILED
        await session.flush()
        logger.warning(
            "seed_kb_document_process_failed",
            document_id=str(document.id),
            error=str(exc),
        )

    logger.info(
        "seed_kb_document_created",
        document_id=str(document.id),
        status=document.status.value,
        chunk_count=document.chunk_count,
    )
    return document
