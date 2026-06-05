"""Stream activity type creation orchestrator responses via Bedrock."""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

import boto3  # pyright: ignore[reportMissingTypeStubs]
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logging import get_logger
from models.activity import ActivityLibraryEntry
from models.instruction import InstructionLevel
from models.user import User
from schemas.activity_assistant import ActivityOrchestratorStreamRequest
from services.activity.bedrock_stream import stream_bedrock_text
from services.activity.charter_loader import load_orchestrator_charter, orchestrator_charter_version
from services.instructions.authoring_context import InstructionAuthoringContext

logger = get_logger(__name__)


class ActivityCreationOrchestrator:
    """Stateless wizard orchestrator for activity type creation."""

    def __init__(self, *, bedrock_client: Any | None = None) -> None:
        self._bedrock = bedrock_client or boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
        )

    async def stream(
        self,
        session: AsyncSession,
        *,
        user: User,
        request: ActivityOrchestratorStreamRequest,
    ) -> AsyncIterator[str | dict[str, Any]]:
        """Stream orchestrator output for the current wizard step."""
        if not request.messages:
            raise ValueError("At least one chat message is required")

        level = InstructionLevel(request.draft.scope_level)
        InstructionAuthoringContext._require_studio_level_write(level, user)

        chat_messages = [
            {"role": message.role, "content": message.content} for message in request.messages
        ]
        system_text = await self._build_system_text(session, request=request, user=user)

        model_id = settings.instruction_authoring_model_id
        started = time.perf_counter()

        logger.info(
            "activity_orchestrator_call_start",
            user_id=str(user.id),
            step=request.step.value,
            charter_version=orchestrator_charter_version(),
            model_id=model_id,
        )

        async for chunk in stream_bedrock_text(
            bedrock_client=self._bedrock,
            model_id=model_id,
            system_text=system_text,
            messages=chat_messages,
        ):
            if isinstance(chunk, dict) and chunk.get("type") == "done":
                latency_ms = int((time.perf_counter() - started) * 1000)
                logger.info(
                    "activity_orchestrator_call_complete",
                    user_id=str(user.id),
                    step=request.step.value,
                    latency_ms=latency_ms,
                )
            yield chunk

    async def _build_system_text(
        self,
        session: AsyncSession,
        *,
        request: ActivityOrchestratorStreamRequest,
        user: User,
    ) -> str:
        draft_json = json.dumps(request.draft.model_dump(), indent=2, default=str)
        catalog = await self._catalog_block(session, request.draft.module_type)

        parts = [
            load_orchestrator_charter(),
            f"## Current wizard step\n{request.step.value}",
            f"## Activity draft (JSON)\n{draft_json}",
            catalog,
            (
                f"## Session\nWorking language: {request.locale}\n"
                f"Scope level: {request.draft.scope_level}"
            ),
        ]
        return "\n\n---\n\n".join(part for part in parts if part.strip())

    async def _catalog_block(
        self,
        session: AsyncSession,
        module_type: str | None,
    ) -> str:
        if not module_type:
            return ""
        result = await session.execute(
            select(ActivityLibraryEntry)
            .where(
                ActivityLibraryEntry.module_type == module_type,
                ActivityLibraryEntry.is_active.is_(True),
            )
            .order_by(ActivityLibraryEntry.display_name.asc()),
        )
        entries = list(result.scalars().all())
        if not entries:
            return "## Existing activity types in module\n(none)"

        lines = ["## Existing activity types in module"]
        for entry in entries:
            lines.append(
                f"- {entry.display_name} (`{entry.thread_type}`, scope={entry.scope})",
            )
        return "\n".join(lines)
