"""Bedrock streaming client for Thread AI conversations."""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

import asyncio
import json
import re
import threading
import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import boto3  # pyright: ignore[reportMissingTypeStubs]
from botocore.exceptions import ClientError  # pyright: ignore[reportMissingTypeStubs]
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logging import get_logger
from models.memory import TaskMemoryEntry, TaskMemoryEntryType
from models.task import Task
from models.thread import MessageRole, Thread, ThreadMessage
from schemas.task_memory import TaskMemoryEntryPayload
from services.ai.context import AssembledContext, ContextAssembler
from services.ai.router import AIRouter

logger = get_logger(__name__)

_TASK_MEMORY_BLOCK_PATTERN = re.compile(
    r"```(?:task_memory|json)\s*\n(\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)


class AIClient:
    """Stream AI responses via AWS Bedrock and persist usage and task memory."""

    def __init__(
        self,
        router: AIRouter | None = None,
        assembler: ContextAssembler | None = None,
        bedrock_client: Any | None = None,
    ) -> None:
        self._router = router or AIRouter()
        self._assembler = assembler or ContextAssembler()
        self._bedrock = bedrock_client or boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
        )

    async def stream(
        self,
        thread: Thread,
        task: Task,
        message: str,
        session: AsyncSession,
        *,
        budget_warning: bool = False,
        workflow_id: UUID | None = None,
    ) -> AsyncIterator[str | dict[str, Any]]:
        """Stream assistant output; persist messages, tokens, and task memory entries."""
        await self._router.ensure_loaded(session, org_id=task.org_id)
        model_id = self._router.get_model(thread.thread_type, budget_warning=budget_warning)
        instruction_version = thread.instruction_version

        context = await self._assembler.assemble(thread, task, message, session)

        user_message = ThreadMessage(
            thread_id=thread.id,
            role=MessageRole.USER,
            content=message,
        )
        session.add(user_message)
        await session.flush()
        instruction_version = context.instruction_version or instruction_version
        request_body = _build_bedrock_request(context)

        started = time.perf_counter()
        logger.info(
            "ai_call_start",
            thread_id=str(thread.id),
            task_id=str(task.id),
            model_id=model_id,
            thread_type=thread.thread_type,
            instruction_version=instruction_version,
            workflow_id=str(workflow_id) if workflow_id else None,
        )

        full_text_parts: list[str] = []
        input_tokens = 0
        output_tokens = 0
        cached_tokens = 0

        try:
            async for event in self._stream_events(model_id, request_body):
                chunk_type = event.get("type")
                if chunk_type == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            full_text_parts.append(text)
                            yield text
                elif chunk_type == "message_delta":
                    usage = event.get("usage", {})
                    output_tokens = int(usage.get("output_tokens", output_tokens))
                elif chunk_type == "message_start":
                    message_usage = event.get("message", {}).get("usage", {})
                    input_tokens = int(message_usage.get("input_tokens", input_tokens))
                    cached_tokens = int(
                        message_usage.get("cache_read_input_tokens", cached_tokens),
                    )
        except ClientError as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            logger.warning(
                "ai_call_failed",
                thread_id=str(thread.id),
                task_id=str(task.id),
                model_id=model_id,
                error=str(exc),
                latency_ms=latency_ms,
            )
            raise RuntimeError("Bedrock streaming request failed") from exc

        full_response = "".join(full_text_parts)
        latency_ms = int((time.perf_counter() - started) * 1000)

        assistant_message = ThreadMessage(
            thread_id=thread.id,
            role=MessageRole.ASSISTANT,
            content=full_response,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            model_id=model_id,
        )
        session.add(assistant_message)

        thread.tokens_used = (thread.tokens_used or 0) + input_tokens + output_tokens
        await session.flush()

        memory_entries = await self._write_task_memory_entries(
            session=session,
            response_text=full_response,
            thread=thread,
            task=task,
            model_id=model_id,
            instruction_version=instruction_version,
        )
        for entry in memory_entries:
            yield {
                "type": "memory_entry",
                "entry": {
                    "id": str(entry.id),
                    "entry_type": entry.entry_type.value,
                    "content": entry.content,
                    "confidence": entry.confidence,
                    "thread_id": str(entry.thread_id),
                    "model_id": entry.model_id,
                    "is_automated": entry.is_automated,
                    "created_at": entry.created_at.isoformat(),
                },
            }
        memory_written = len(memory_entries)

        logger.info(
            "ai_call_complete",
            thread_id=str(thread.id),
            task_id=str(task.id),
            model_id=model_id,
            instruction_version=instruction_version,
            thread_type=thread.thread_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            latency_ms=latency_ms,
            workflow_id=str(workflow_id) if workflow_id else None,
            memory_entries_written=memory_written,
        )

        yield {
            "type": "done",
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cached_tokens": cached_tokens,
            "model_id": model_id,
        }

    async def _stream_events(
        self,
        model_id: str,
        request_body: dict[str, Any],
    ) -> AsyncIterator[dict[str, Any]]:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()

        def _producer() -> None:
            try:
                response = self._bedrock.invoke_model_with_response_stream(
                    modelId=model_id,
                    body=json.dumps(request_body),
                    contentType="application/json",
                    accept="application/json",
                )
                for event in response["body"]:
                    chunk_bytes = event.get("chunk", {}).get("bytes")
                    if chunk_bytes:
                        payload = json.loads(chunk_bytes)
                        loop.call_soon_threadsafe(queue.put_nowait, ("event", payload))
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, ("done", None))

        worker = threading.Thread(target=_producer, daemon=True)
        worker.start()

        while True:
            kind, payload = await queue.get()
            if kind == "done":
                break
            if kind == "error":
                raise payload
            yield payload

    async def _write_task_memory_entries(
        self,
        *,
        session: AsyncSession,
        response_text: str,
        thread: Thread,
        task: Task,
        model_id: str,
        instruction_version: str | None,
    ) -> list[TaskMemoryEntry]:
        written: list[TaskMemoryEntry] = []
        for raw_json in _extract_task_memory_json(response_text):
            try:
                data = json.loads(raw_json)
                payload = TaskMemoryEntryPayload.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                logger.warning(
                    "task_memory_validation_failed",
                    thread_id=str(thread.id),
                    task_id=str(task.id),
                    error=str(exc),
                    raw=raw_json[:500],
                )
                continue

            entry = TaskMemoryEntry(
                org_id=task.org_id,
                task_id=task.id,
                thread_id=thread.id,
                entry_type=TaskMemoryEntryType(payload.type.value),
                content=payload.content,
                confidence=payload.confidence,
                source_chunk_ids=payload.source_chunk_ids,
                model_id=payload.model_id or model_id,
                instruction_version=payload.instruction_version or instruction_version,
                is_automated=thread.is_automated,
            )
            session.add(entry)
            written.append(entry)
            logger.info(
                "task_memory_entry_written",
                thread_id=str(thread.id),
                task_id=str(task.id),
                entry_type=payload.type.value,
            )

        if written:
            await session.flush()
        return written

def _build_bedrock_request(context: AssembledContext) -> dict[str, Any]:
    context_text = "\n\n".join(block for block in context.context_blocks if block)
    user_parts = []
    if context_text:
        user_parts.append(context_text)
    user_parts.append(context.current_message)
    final_user_content = "\n\n---\n\n".join(user_parts)

    api_messages = list(context.messages)
    api_messages.append({"role": "user", "content": final_user_content})

    body: dict[str, Any] = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": settings.bedrock_max_output_tokens,
        "messages": api_messages,
    }
    if context.system_blocks:
        body["system"] = context.system_blocks
    return body


def _extract_task_memory_json(response_text: str) -> list[str]:
    blocks = _TASK_MEMORY_BLOCK_PATTERN.findall(response_text)
    if blocks:
        return blocks

    candidates: list[str] = []
    for line in response_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("{") and '"type"' in stripped:
            candidates.append(stripped)
    return candidates
