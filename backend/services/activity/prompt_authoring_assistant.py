"""Stream activity prompt authoring assistant responses via Bedrock."""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from typing import Any

import boto3  # pyright: ignore[reportMissingTypeStubs]
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logging import get_logger
from models.user import User
from schemas.prompt_assistant import PromptAssistantStreamRequest
from services.activity.bedrock_stream import stream_bedrock_text
from services.activity.prompt_authoring_context import PromptAuthoringContext

logger = get_logger(__name__)


class ActivityPromptAuthoringAssistant:
    """Stateless prompt authoring assistant."""

    def __init__(
        self,
        *,
        context_builder: PromptAuthoringContext | None = None,
        bedrock_client: Any | None = None,
    ) -> None:
        self._context_builder = context_builder or PromptAuthoringContext()
        self._bedrock = bedrock_client or boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
        )

    async def stream(
        self,
        session: AsyncSession,
        *,
        user: User,
        request: PromptAssistantStreamRequest,
    ) -> AsyncIterator[str | dict[str, Any]]:
        """Stream assistant output for a prompt authoring session."""
        if not request.messages:
            raise ValueError("At least one chat message is required")

        chat_messages = [
            {"role": message.role, "content": message.content} for message in request.messages
        ]
        draft_prompts = [
            {
                "prompt_text": item.prompt_text,
                "stage": item.stage,
            }
            for item in request.draft_prompts
        ]
        context = await self._context_builder.build(
            session,
            scope=request.scope,
            user=user,
            draft_prompts=draft_prompts,
            chat_messages=chat_messages,
            locale=request.locale,
        )

        model_id = settings.instruction_authoring_model_id
        started = time.perf_counter()

        logger.info(
            "prompt_authoring_call_start",
            user_id=str(user.id),
            mode=request.scope.authoring_mode.value,
            thread_type=request.scope.thread_type,
            charter_version=context.charter_version,
            model_id=model_id,
        )

        async for chunk in stream_bedrock_text(
            bedrock_client=self._bedrock,
            model_id=model_id,
            system_text=context.system_text,
            messages=context.messages,
        ):
            if isinstance(chunk, dict) and chunk.get("type") == "done":
                latency_ms = int((time.perf_counter() - started) * 1000)
                logger.info(
                    "prompt_authoring_call_complete",
                    user_id=str(user.id),
                    model_id=model_id,
                    input_tokens=chunk.get("input_tokens", 0),
                    output_tokens=chunk.get("output_tokens", 0),
                    latency_ms=latency_ms,
                )
            yield chunk
