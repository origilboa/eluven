"""Stream instruction authoring assistant responses via Bedrock."""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

import asyncio
import json
import threading
import time
from collections.abc import AsyncIterator
from typing import Any

import boto3  # pyright: ignore[reportMissingTypeStubs]
from botocore.exceptions import ClientError  # pyright: ignore[reportMissingTypeStubs]
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logging import get_logger
from models.user import User
from schemas.instruction_assistant import InstructionAssistantStreamRequest
from services.instructions.authoring_context import (
    AuthoringAssembledContext,
    InstructionAuthoringContext,
)

logger = get_logger(__name__)


def _bedrock_stream_error_message(exc: BaseException) -> str:
    """Map Bedrock client errors to user-facing stream messages."""
    if isinstance(exc, ClientError):
        error_message = exc.response.get("Error", {}).get("Message", str(exc))
        if "use case" in error_message.lower():
            return (
                "This AI model is not enabled for your AWS account yet. "
                "Complete the Anthropic use-case form in the Bedrock console, "
                "or contact your administrator."
            )
        return f"Bedrock request failed: {error_message}"
    return "Bedrock streaming request failed"


class InstructionAuthoringAssistant:
    """Stateless instruction authoring assistant — no DB persistence of chat."""

    def __init__(
        self,
        *,
        context_builder: InstructionAuthoringContext | None = None,
        bedrock_client: Any | None = None,
    ) -> None:
        self._context_builder = context_builder or InstructionAuthoringContext()
        self._bedrock = bedrock_client or boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
        )

    async def stream(
        self,
        session: AsyncSession,
        *,
        user: User,
        request: InstructionAssistantStreamRequest,
    ) -> AsyncIterator[str | dict[str, Any]]:
        """Stream assistant output for an authoring session."""
        chat_messages = [
            {"role": message.role, "content": message.content}
            for message in request.messages
        ]
        if not chat_messages:
            raise ValueError("At least one chat message is required")

        context = await self._context_builder.build(
            session,
            scope=request.scope,
            user=user,
            draft_content=request.draft_content,
            chat_messages=chat_messages,
            locale=request.locale,
            integrity_review=request.integrity_review,
            completeness_review=request.completeness_review,
        )

        async for chunk in self._stream_with_context(
            session,
            user=user,
            context=context,
            request=request,
        ):
            yield chunk

    async def _stream_with_context(
        self,
        session: AsyncSession,
        *,
        user: User,
        context: AuthoringAssembledContext,
        request: InstructionAssistantStreamRequest,
    ) -> AsyncIterator[str | dict[str, Any]]:
        """Stream Bedrock output for a pre-assembled authoring context."""
        _ = session
        model_id = settings.instruction_authoring_model_id
        request_body = _build_bedrock_request(context)
        started = time.perf_counter()

        logger.info(
            "instruction_authoring_call_start",
            user_id=str(user.id),
            level=context.editable_level.value,
            thread_type=request.scope.thread_type,
            charter_version=context.charter_version,
            model_id=model_id,
            integrity_review=request.integrity_review,
            completeness_review=request.completeness_review,
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
                "instruction_authoring_call_failed",
                user_id=str(user.id),
                level=context.editable_level.value,
                model_id=model_id,
                error=str(exc),
                latency_ms=latency_ms,
            )
            raise RuntimeError(_bedrock_stream_error_message(exc)) from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "instruction_authoring_call_complete",
            user_id=str(user.id),
            level=context.editable_level.value,
            thread_type=request.scope.thread_type,
            charter_version=context.charter_version,
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            latency_ms=latency_ms,
            response_length=len("".join(full_text_parts)),
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


def _build_bedrock_request(context: AuthoringAssembledContext) -> dict[str, Any]:
    return {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": settings.bedrock_max_output_tokens,
        "system": context.system_text,
        "messages": context.messages,
    }
