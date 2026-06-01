"""SQS enqueue helpers for workflow execution."""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

import json
from uuid import UUID

import boto3  # pyright: ignore[reportMissingTypeStubs]

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)


def get_workflow_execution_queue_url() -> str:
    """Resolve WorkflowExecution queue URL from settings or SST Resource."""
    if settings.workflow_execution_queue_url:
        return settings.workflow_execution_queue_url

    try:
        from sst import Resource

        return Resource.WorkflowExecution.url
    except Exception as exc:
        raise RuntimeError(
            "Workflow execution queue URL is not configured. "
            "Set WORKFLOW_EXECUTION_QUEUE_URL or link the SST WorkflowExecution queue.",
        ) from exc


def enqueue_workflow_thread(
    workflow_execution_id: UUID,
    thread_execution_id: UUID,
) -> None:
    """Enqueue a workflow thread step for async execution."""
    queue_url = get_workflow_execution_queue_url()
    message = json.dumps(
        {
            "workflow_execution_id": str(workflow_execution_id),
            "thread_execution_id": str(thread_execution_id),
        },
    )
    client = boto3.client("sqs", region_name=settings.aws_region)
    client.send_message(QueueUrl=queue_url, MessageBody=message)
    logger.info(
        "workflow_thread_enqueued",
        workflow_execution_id=str(workflow_execution_id),
        thread_execution_id=str(thread_execution_id),
    )
