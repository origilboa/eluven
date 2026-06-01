#!/usr/bin/env python3
"""SQS worker for automated workflow thread execution."""

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
from core.database import AsyncSessionLocal
from core.logging import configure_logging, get_logger
from services.workflow.engine import WorkflowEngine, WorkflowEngineError
from services.workflow.queue import get_workflow_execution_queue_url

logger = get_logger(__name__)

POLL_WAIT_SECONDS = 20


async def _process_payload(payload: dict[str, Any]) -> bool:
    """Execute one workflow thread step. Returns True when processing finished cleanly."""
    workflow_execution_id = UUID(str(payload["workflow_execution_id"]))
    thread_execution_id = UUID(str(payload["thread_execution_id"]))

    engine = WorkflowEngine()
    async with AsyncSessionLocal() as session:
        try:
            await engine.execute_thread(
                workflow_execution_id,
                thread_execution_id,
                session,
            )
            await session.commit()
            return True
        except WorkflowEngineError as exc:
            await session.commit()
            logger.warning(
                "workflow_thread_processing_failed",
                workflow_execution_id=str(workflow_execution_id),
                thread_execution_id=str(thread_execution_id),
                error=str(exc),
            )
            return True
        except Exception as exc:
            await session.rollback()
            logger.warning(
                "workflow_thread_processing_failed",
                workflow_execution_id=str(workflow_execution_id),
                thread_execution_id=str(thread_execution_id),
                error=str(exc),
            )
            return False


def _handle_message(body: str) -> bool:
    """Process one SQS message body."""
    try:
        payload = json.loads(body)
        workflow_execution_id = payload.get("workflow_execution_id")
        thread_execution_id = payload.get("thread_execution_id")
        if not workflow_execution_id or not thread_execution_id:
            raise ValueError(
                "Invalid message: missing workflow_execution_id or thread_execution_id",
            )

        logger.info(
            "workflow_thread_processing_started",
            workflow_execution_id=str(workflow_execution_id),
            thread_execution_id=str(thread_execution_id),
        )
        return asyncio.run(_process_payload(payload))
    except Exception as exc:
        logger.warning("workflow_thread_processing_failed", error=str(exc))
        return False


def run_worker() -> None:
    """Poll WorkflowExecution SQS queue until interrupted."""
    configure_logging()
    queue_url = get_workflow_execution_queue_url()
    sqs = boto3.client("sqs", region_name=settings.aws_region)

    logger.info("workflow_worker_started", queue_url=queue_url)

    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=POLL_WAIT_SECONDS,
                MessageAttributeNames=["All"],
            )
        except ClientError as exc:
            logger.error("workflow_worker_receive_failed", error=str(exc))
            continue

        messages = response.get("Messages", [])
        if not messages:
            continue

        for message in messages:
            receipt_handle = message["ReceiptHandle"]
            body = message.get("Body", "")
            success = _handle_message(body)

            if success:
                sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
                logger.info("workflow_worker_message_deleted", receipt_handle=receipt_handle)
            else:
                logger.info(
                    "workflow_worker_message_retained",
                    receipt_handle=receipt_handle,
                )


def main() -> None:
    """Entry point for the workflow execution worker."""
    run_worker()


if __name__ == "__main__":
    main()
