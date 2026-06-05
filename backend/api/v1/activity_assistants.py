"""SSE endpoints for activity studio Layer 0 agents."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user, get_db
from core.config import settings
from core.logging import get_logger
from models.user import User
from schemas.activity_assistant import ActivityOrchestratorStreamRequest
from schemas.prompt_assistant import PromptAssistantStreamRequest
from services.activity.creation_orchestrator import ActivityCreationOrchestrator
from services.activity.prompt_authoring_assistant import ActivityPromptAuthoringAssistant

logger = get_logger(__name__)

router = APIRouter(prefix="/activity-library", tags=["activity-assistants"])


def _sse_line(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/prompts/assistant/stream")
async def stream_prompt_authoring_assistant(
    body: PromptAssistantStreamRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Stream activity prompt authoring assistant responses via SSE."""
    if not body.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one chat message is required",
        )
    if len(body.messages) > settings.instruction_authoring_max_messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"At most {settings.instruction_authoring_max_messages} messages allowed",
        )

    assistant = ActivityPromptAuthoringAssistant()

    async def event_generator() -> AsyncIterator[str]:
        try:
            yield _sse_line({"type": "status", "message": "Preparing response..."})
            async for chunk in assistant.stream(db, user=current_user, request=body):
                if isinstance(chunk, str):
                    yield _sse_line({"type": "text", "text": chunk})
                    continue
                if chunk.get("type") == "done":
                    yield _sse_line(
                        {
                            "type": "done",
                            "input_tokens": chunk.get("input_tokens", 0),
                            "output_tokens": chunk.get("output_tokens", 0),
                            "cached_tokens": chunk.get("cached_tokens", 0),
                        },
                    )
        except HTTPException as exc:
            yield _sse_line({"type": "error", "message": str(exc.detail)})
        except Exception as exc:
            logger.exception("prompt_authoring_stream_error", user_id=str(current_user.id))
            yield _sse_line({"type": "error", "message": str(exc)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/assistant/stream")
async def stream_activity_orchestrator(
    body: ActivityOrchestratorStreamRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Stream activity type creation orchestrator responses via SSE."""
    if not body.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one chat message is required",
        )
    if len(body.messages) > settings.instruction_authoring_max_messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"At most {settings.instruction_authoring_max_messages} messages allowed",
        )

    orchestrator = ActivityCreationOrchestrator()

    async def event_generator() -> AsyncIterator[str]:
        try:
            yield _sse_line({"type": "status", "message": "Preparing response..."})
            async for chunk in orchestrator.stream(db, user=current_user, request=body):
                if isinstance(chunk, str):
                    yield _sse_line({"type": "text", "text": chunk})
                    continue
                if chunk.get("type") == "done":
                    yield _sse_line(
                        {
                            "type": "done",
                            "input_tokens": chunk.get("input_tokens", 0),
                            "output_tokens": chunk.get("output_tokens", 0),
                            "cached_tokens": chunk.get("cached_tokens", 0),
                        },
                    )
        except HTTPException as exc:
            yield _sse_line({"type": "error", "message": str(exc.detail)})
        except Exception as exc:
            logger.exception("activity_orchestrator_stream_error", user_id=str(current_user.id))
            yield _sse_line({"type": "error", "message": str(exc)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")
