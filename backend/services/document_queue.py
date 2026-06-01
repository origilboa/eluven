"""SQS enqueue helpers for document processing."""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

import json
from typing import Literal
from uuid import UUID

import boto3  # pyright: ignore[reportMissingTypeStubs]

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

DocumentType = Literal["kb", "thread"]


def get_document_processing_queue_url() -> str:
    """Resolve DocumentProcessing queue URL from settings or SST Resource."""
    if settings.document_processing_queue_url:
        return settings.document_processing_queue_url

    try:
        from sst import Resource

        return Resource.DocumentProcessing.url
    except Exception as exc:
        raise RuntimeError(
            "Document processing queue URL is not configured. "
            "Set DOCUMENT_PROCESSING_QUEUE_URL or link the SST DocumentProcessing queue.",
        ) from exc


def enqueue_document_processing(document_id: UUID, document_type: DocumentType) -> None:
    """Enqueue a document for async indexing."""
    queue_url = get_document_processing_queue_url()
    message = json.dumps(
        {
            "document_id": str(document_id),
            "document_type": document_type,
        },
    )
    client = boto3.client("sqs", region_name=settings.aws_region)
    client.send_message(QueueUrl=queue_url, MessageBody=message)
    logger.info(
        "document_enqueued",
        document_id=str(document_id),
        document_type=document_type,
    )
