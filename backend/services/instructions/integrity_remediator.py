"""Stream instruction integrity remediation chat."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from schemas.instruction_assistant import (
    InstructionAssistantStreamRequest,
    InstructionIntegrityRemediateRequest,
)
from services.instructions.authoring_assistant import InstructionAuthoringAssistant


class InstructionIntegrityRemediator:
    """Guide users to fix integrity issues with optional auto-fix proposals."""

    def __init__(self, *, assistant: InstructionAuthoringAssistant | None = None) -> None:
        self._assistant = assistant or InstructionAuthoringAssistant()

    async def stream(
        self,
        session: AsyncSession,
        *,
        user: User,
        request: InstructionIntegrityRemediateRequest,
    ) -> AsyncIterator[str | dict[str, Any]]:
        """Stream remediation guidance; may propose draft fixes."""
        if not request.messages:
            raise ValueError("At least one chat message is required")

        issues_json = json.dumps(
            [issue.model_dump() for issue in request.issues],
            default=str,
        )
        stream_request = InstructionAssistantStreamRequest(
            scope=request.scope,
            draft_content=request.draft_content,
            messages=request.messages,
            locale=request.locale,
        )

        chat_messages = [
            {"role": message.role, "content": message.content}
            for message in request.messages
        ]
        context = await self._assistant._context_builder.build(  # noqa: SLF001
            session,
            scope=request.scope,
            user=user,
            draft_content=request.draft_content,
            chat_messages=chat_messages,
            locale=request.locale,
            integrity_remediation=True,
            integrity_issues_json=issues_json,
        )

        async for chunk in self._assistant._stream_with_context(  # noqa: SLF001
            session,
            user=user,
            context=context,
            request=stream_request,
        ):
            yield chunk
