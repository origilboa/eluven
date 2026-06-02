#!/usr/bin/env python3
"""SQS worker for KB and thread document processing."""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import boto3  # pyright: ignore[reportMissingTypeStubs]
from botocore.exceptions import ClientError  # pyright: ignore[reportMissingTypeStubs]

from core.config import settings
from core.database import AsyncSessionLocal, engine
from core.logging import configure_logging, get_logger
from services.document.processor import DocumentNotFoundError, DocumentProcessor
from services.document_queue import get_document_processing_queue_url

logger = get_logger(__name__)

POLL_WAIT_SECONDS = 20
DOCUMENT_TYPE_KB = "kb"
DOCUMENT_TYPE_THREAD = "thread"
DOCUMENT_TYPE_TASK = "task"


async def _process_payload(payload: dict[str, Any]) -> None:
    """Run DocumentProcessor for a single queue message."""
    document_id = UUID(str(payload["document_id"]))
    document_type = str(payload["document_type"])

    processor = DocumentProcessor()
    async with AsyncSessionLocal() as session:
        try:
            if document_type == DOCUMENT_TYPE_KB:
                await processor.process_kb_document(document_id, session)
            elif document_type == DOCUMENT_TYPE_THREAD:
                await processor.process_thread_document(document_id, session)
            elif document_type == DOCUMENT_TYPE_TASK:
                await processor.process_task_document(document_id, session)
            else:
                raise ValueError(f"Unknown document_type: {document_type}")
        except DocumentNotFoundError as exc:
            logger.warning(
                "document_processing_failed",
                document_id=str(document_id),
                document_type=document_type,
                error=str(exc),
            )
        except Exception as exc:
            logger.warning(
                "document_processing_failed",
                document_id=str(document_id),
                document_type=document_type,
                error=str(exc),
            )
        await session.commit()


async def _handle_message(body: str) -> bool:
    """Process one SQS message body. Returns True on success."""
    try:
        payload = json.loads(body)
        document_id = payload.get("document_id")
        document_type = payload.get("document_type")
        if not document_id or not document_type:
            raise ValueError("Invalid message: missing document_id or document_type")

        logger.info(
            "document_processing_started",
            document_id=str(document_id),
            document_type=document_type,
        )
        await _process_payload(payload)
        logger.info(
            "document_processed",
            document_id=str(document_id),
            document_type=document_type,
        )
        return True
    except Exception as exc:
        logger.warning("document_processing_failed", error=str(exc))
        return False


async def run_worker_async() -> None:
    """Poll DocumentProcessing SQS queue until interrupted."""
    configure_logging()
    queue_url = get_document_processing_queue_url()
    sqs = boto3.client("sqs", region_name=settings.aws_region)

    logger.info("document_worker_started", queue_url=queue_url)

    while True:
        try:
            response = await asyncio.to_thread(
                sqs.receive_message,
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=POLL_WAIT_SECONDS,
                MessageAttributeNames=["All"],
            )
        except ClientError as exc:
            logger.error("document_worker_receive_failed", error=str(exc))
            continue

        messages = response.get("Messages", [])
        if not messages:
            continue

        for message in messages:
            receipt_handle = message["ReceiptHandle"]
            body = message.get("Body", "")
            success = await _handle_message(body)

            if success:
                await asyncio.to_thread(
                    sqs.delete_message,
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle,
                )
                logger.info("document_worker_message_deleted", receipt_handle=receipt_handle)
            else:
                logger.info(
                    "document_worker_message_retained",
                    receipt_handle=receipt_handle,
                )


def run_worker() -> None:
    """Entry point wrapper for async worker loop."""
    try:
        asyncio.run(run_worker_async())
    finally:
        asyncio.run(engine.dispose())


def main() -> None:
    """Entry point for the document processing worker."""
    run_worker()


if __name__ == "__main__":
    main()
