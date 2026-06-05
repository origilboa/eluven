"""Assemble context for the activity prompt authoring assistant."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.activity import ActivityLibraryEntry, ActivityPrompt
from models.instruction import InstructionLevel
from models.user import User
from schemas.prompt_assistant import PromptAssistantScope
from services.activity.charter_loader import load_prompt_authoring_charter, prompt_charter_version
from services.instructions.authoring_context import InstructionAuthoringContext

_MODULE_TYPES = frozenset({"external_paper_review", "student_paper_review"})


@dataclass
class PromptAuthoringAssembledContext:
    """Bedrock-ready prompt authoring context."""

    system_text: str
    messages: list[dict[str, str]]
    charter_version: str


class PromptAuthoringContext:
    """Build prompt authoring assistant system prompts."""

    def __init__(self) -> None:
        self._instruction_context = InstructionAuthoringContext()

    async def build(
        self,
        session: AsyncSession,
        *,
        scope: PromptAssistantScope,
        user: User,
        draft_prompts: list[dict[str, str]],
        chat_messages: list[dict[str, str]],
        locale: str,
    ) -> PromptAuthoringAssembledContext:
        """Resolve scope, auth, and compose system prompt."""
        if scope.level not in ("platform", "org"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt authoring requires platform or org level",
            )
        InstructionAuthoringContext._require_studio_level_write(
            InstructionLevel(scope.level),
            user,
        )

        thread_type = scope.thread_type
        module_type = scope.module_type
        supports_automation = scope.supports_automation
        instruction_content = scope.default_instruction_content
        entry: ActivityLibraryEntry | None = None

        if scope.activity_draft:
            draft = scope.activity_draft
            thread_type = thread_type or draft.thread_type
            module_type = module_type or draft.module_type
            if draft.supports_automation is not None:
                supports_automation = draft.supports_automation

        if scope.activity_entry_id:
            entry = await session.get(ActivityLibraryEntry, UUID(scope.activity_entry_id))
            if entry is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Activity entry not found",
                )
            await InstructionAuthoringContext._require_activity_entry_access(entry, user)
            thread_type = entry.thread_type
            module_type = entry.module_type
            supports_automation = entry.supports_automation
            instruction_content = instruction_content or entry.default_instruction_content

        if not thread_type or not module_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="thread_type and module_type are required",
            )
        if module_type not in _MODULE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid module_type",
            )

        existing_prompt_lines = self._format_draft_prompts(draft_prompts)
        if entry is not None and not draft_prompts:
            existing_prompt_lines = await self._format_saved_prompts(session, entry.id)

        examples = await self._sibling_prompt_examples(session, module_type, thread_type)

        metadata_lines = [
            "## Scope metadata",
            f"Authoring mode: {scope.authoring_mode.value}",
            f"Module type: {module_type}",
            f"Thread type: {thread_type}",
            f"Supports automation: {supports_automation}",
        ]
        if scope.activity_draft and scope.activity_draft.display_name:
            metadata_lines.append(f"Display name: {scope.activity_draft.display_name}")
        if scope.activity_draft and scope.activity_draft.description:
            metadata_lines.append(f"Description: {scope.activity_draft.description}")
        if entry is not None:
            metadata_lines.append(f"Activity entry id: {entry.id}")
            metadata_lines.append(f"Display name: {entry.display_name}")

        instruction_block = ""
        if instruction_content and instruction_content.strip():
            instruction_block = (
                "## Activity instructions (reference only — do not duplicate as prompts)\n"
                f"{instruction_content.strip()}"
            )

        system_parts = [
            load_prompt_authoring_charter(),
            "\n".join(metadata_lines),
            instruction_block,
            examples,
            f"## Current prompt draft\n{existing_prompt_lines or '(empty)'}",
            f"## Session\nWorking language: {locale}",
        ]
        system_text = "\n\n---\n\n".join(part for part in system_parts if part.strip())

        return PromptAuthoringAssembledContext(
            system_text=system_text,
            messages=chat_messages,
            charter_version=prompt_charter_version(),
        )

    @staticmethod
    def _format_draft_prompts(prompts: list[dict[str, str]]) -> str:
        if not prompts:
            return ""
        lines: list[str] = []
        for index, item in enumerate(prompts, start=1):
            stage = item.get("stage", "opening")
            text = item.get("prompt_text", "").strip()
            if text:
                lines.append(f"{index}. [{stage}] {text}")
        return "\n".join(lines)

    async def _format_saved_prompts(
        self,
        session: AsyncSession,
        entry_id: UUID,
    ) -> str:
        result = await session.execute(
            select(ActivityPrompt)
            .where(ActivityPrompt.activity_entry_id == entry_id)
            .order_by(ActivityPrompt.sequence_index.asc()),
        )
        prompts = list(result.scalars().all())
        lines: list[str] = []
        for index, prompt in enumerate(prompts, start=1):
            lines.append(f"{index}. [{prompt.stage.value}] {prompt.prompt_text}")
        return "\n".join(lines)

    async def _sibling_prompt_examples(
        self,
        session: AsyncSession,
        module_type: str,
        exclude_thread_type: str,
    ) -> str:
        entries_result = await session.execute(
            select(ActivityLibraryEntry)
            .where(
                ActivityLibraryEntry.module_type == module_type,
                ActivityLibraryEntry.is_active.is_(True),
                ActivityLibraryEntry.thread_type != exclude_thread_type,
            )
            .limit(3),
        )
        entries = list(entries_result.scalars().all())
        if not entries:
            return ""

        blocks: list[str] = ["## Reference prompt sets (same module)"]
        for entry in entries:
            prompts_result = await session.execute(
                select(ActivityPrompt)
                .where(ActivityPrompt.activity_entry_id == entry.id)
                .order_by(ActivityPrompt.sequence_index.asc())
                .limit(3),
            )
            prompts = list(prompts_result.scalars().all())
            if not prompts:
                continue
            lines = [f"- [{prompt.stage.value}] {prompt.prompt_text}" for prompt in prompts]
            blocks.append(
                f"### {entry.display_name} ({entry.thread_type})\n" + "\n".join(lines),
            )
        return "\n\n".join(blocks) if len(blocks) > 1 else ""
