"""Assemble context for the instruction authoring assistant."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.access import get_owned_cluster, get_owned_task, get_owned_thread
from models.activity import ActivityLibraryEntry
from models.instruction import InstructionLevel, InstructionSet, InstructionVersion
from models.task import Task
from models.user import User, UserRole
from schemas.instruction_assistant import (
    AuthoringTarget,
    InstructionAssistantScope,
)
from services.instructions.prompt_loader import load_charter_text, load_level_brief

_THREAD_TYPE_PARENT_LEVELS = frozenset(
    {
        InstructionLevel.PLATFORM,
        InstructionLevel.ORG,
        InstructionLevel.USER,
        InstructionLevel.CLUSTER,
    },
)
_ORG_SCOPED_LEVELS = frozenset(
    {
        InstructionLevel.ORG,
        InstructionLevel.USER,
        InstructionLevel.CLUSTER,
        InstructionLevel.TASK,
        InstructionLevel.THREAD,
    },
)
_TASK_SCOPED_LEVELS = frozenset({InstructionLevel.CLUSTER, InstructionLevel.TASK})

_PARENT_LEVELS: dict[InstructionLevel, tuple[InstructionLevel, ...]] = {
    InstructionLevel.PLATFORM: (),
    InstructionLevel.ORG: (InstructionLevel.PLATFORM,),
    InstructionLevel.USER: (InstructionLevel.PLATFORM, InstructionLevel.ORG),
    InstructionLevel.CLUSTER: (
        InstructionLevel.PLATFORM,
        InstructionLevel.ORG,
        InstructionLevel.USER,
    ),
    InstructionLevel.TASK: (
        InstructionLevel.PLATFORM,
        InstructionLevel.ORG,
        InstructionLevel.USER,
        InstructionLevel.CLUSTER,
    ),
    InstructionLevel.THREAD: (
        InstructionLevel.PLATFORM,
        InstructionLevel.ORG,
        InstructionLevel.USER,
        InstructionLevel.CLUSTER,
        InstructionLevel.TASK,
    ),
}


@dataclass
class AuthoringAssembledContext:
    """Bedrock-ready authoring context."""

    system_text: str
    messages: list[dict[str, str]]
    charter_version: str
    editable_level: InstructionLevel


class InstructionAuthoringContext:
    """Build authoring assistant prompts from scope and database state."""

    async def build(
        self,
        session: AsyncSession,
        *,
        scope: InstructionAssistantScope,
        user: User,
        draft_content: str,
        chat_messages: list[dict[str, str]],
        locale: str,
    ) -> AuthoringAssembledContext:
        """Resolve scope, auth, and compose system prompt."""
        if scope.authoring_target == AuthoringTarget.ACTIVITY_LIBRARY_DEFAULT:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Activity library authoring target is not implemented yet",
            )

        editable_level = InstructionLevel(scope.level)
        context = await self._resolve_entity_context(session, scope=scope, user=user)

        inherited_blocks: list[str] = []
        for parent_level in _PARENT_LEVELS[editable_level]:
            if parent_level == InstructionLevel.CLUSTER and context.cluster_id is None:
                continue
            parent_text = await self._instruction_for_level(
                session,
                parent_level,
                org_id=context.org_id,
                thread_type=context.resolved_thread_type
                if parent_level in _THREAD_TYPE_PARENT_LEVELS
                else None,
                owner_org_id=context.org_id if parent_level == InstructionLevel.ORG else None,
                user_id=context.owner_user_id if parent_level == InstructionLevel.USER else None,
                cluster_id=context.cluster_id if parent_level == InstructionLevel.CLUSTER else None,
                task_id=context.task_id if parent_level == InstructionLevel.TASK else None,
                task_thread_type=context.task_thread_type_filter,
            )
            if parent_text:
                inherited_blocks.append(
                    f"## Inherited: {parent_level.value}\n{parent_text}",
                )

        metadata_block = await self._metadata_block(session, context=context, scope=scope)
        level_brief = load_level_brief(editable_level)
        charter = load_charter_text()

        system_parts = [
            charter,
            f"## Level brief ({editable_level.value})\n{level_brief}".strip()
            if level_brief
            else "",
            f"## Session\nEditable layer: {editable_level.value}\nWorking language: {locale}",
            metadata_block,
            "\n\n".join(inherited_blocks),
            f"## Current draft ({editable_level.value} only)\n{draft_content}".strip()
            if draft_content.strip()
            else f"## Current draft ({editable_level.value} only)\n(empty)",
        ]
        system_text = "\n\n---\n\n".join(part for part in system_parts if part.strip())

        from services.instructions.prompt_loader import charter_version

        return AuthoringAssembledContext(
            system_text=system_text,
            messages=chat_messages,
            charter_version=charter_version(),
            editable_level=editable_level,
        )

    async def _resolve_entity_context(
        self,
        session: AsyncSession,
        *,
        scope: InstructionAssistantScope,
        user: User,
    ) -> _EntityContext:
        editable_level = InstructionLevel(scope.level)
        org_id = user.org_id
        owner_user_id = user.id
        cluster_id: UUID | None = None
        task_id: UUID | None = None
        thread_id: UUID | None = None
        module_type = scope.module_type
        resolved_thread_type = scope.thread_type
        task_thread_type_filter: str | None = None
        entity_title: str | None = None

        if editable_level == InstructionLevel.PLATFORM:
            self._require_studio_level_write(editable_level, user)
        elif editable_level == InstructionLevel.ORG:
            self._require_studio_level_write(editable_level, user)
        elif editable_level == InstructionLevel.USER:
            self._require_studio_level_write(editable_level, user)
        elif editable_level == InstructionLevel.CLUSTER:
            if not scope.cluster_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="cluster_id is required for cluster authoring",
                )
            cluster = await get_owned_cluster(session, UUID(scope.cluster_id), user)
            cluster_id = cluster.id
            module_type = module_type or cluster.module_type
            entity_title = cluster.title
            task_thread_type_filter = resolved_thread_type
        elif editable_level == InstructionLevel.TASK:
            if not scope.task_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="task_id is required for task authoring",
                )
            task = await get_owned_task(session, UUID(scope.task_id), user)
            task_id = task.id
            cluster_id = task.cluster_id
            module_type = module_type or task.module_type
            entity_title = task.title
            task_thread_type_filter = resolved_thread_type
        elif editable_level == InstructionLevel.THREAD:
            if not scope.thread_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="thread_id is required for thread authoring",
                )
            thread = await get_owned_thread(session, UUID(scope.thread_id), user)
            thread_id = thread.id
            task = await session.get(Task, thread.task_id)
            if task is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found",
                )
            task_id = task.id
            cluster_id = task.cluster_id
            module_type = module_type or task.module_type
            resolved_thread_type = resolved_thread_type or thread.thread_type
            entity_title = thread.title
            owner_user_id = thread.owner_id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported instruction level: {scope.level}",
            )

        return _EntityContext(
            org_id=org_id,
            owner_user_id=owner_user_id,
            cluster_id=cluster_id,
            task_id=task_id,
            thread_id=thread_id,
            module_type=module_type,
            resolved_thread_type=resolved_thread_type,
            task_thread_type_filter=task_thread_type_filter,
            entity_title=entity_title,
        )

    @staticmethod
    def _require_studio_level_write(level: InstructionLevel, user: User) -> None:
        if level == InstructionLevel.PLATFORM and user.role != UserRole.APP_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform instructions require app admin access",
            )
        if level == InstructionLevel.ORG and user.role not in (
            UserRole.ORG_ADMIN,
            UserRole.APP_ADMIN,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization instructions require org admin access",
            )

    async def _metadata_block(
        self,
        session: AsyncSession,
        *,
        context: _EntityContext,
        scope: InstructionAssistantScope,
    ) -> str:
        lines = ["## Scope metadata"]
        if context.entity_title:
            lines.append(f"Entity title: {context.entity_title}")
        if context.module_type:
            lines.append(f"Module type: {context.module_type}")
        if context.resolved_thread_type:
            lines.append(f"Thread type: {context.resolved_thread_type}")

        activity = await self._activity_entry(
            session,
            org_id=context.org_id,
            thread_type=context.resolved_thread_type,
            module_type=context.module_type,
            activity_entry_id=scope.activity_entry_id,
        )
        if activity is not None:
            lines.append(f"Activity display name: {activity.display_name}")
            if activity.description:
                lines.append(f"Activity description: {activity.description}")
            if activity.default_instruction_content:
                lines.append(
                    "Activity default instruction template:\n"
                    f"{activity.default_instruction_content}",
                )
        elif scope.activity_draft:
            draft = scope.activity_draft
            if draft.display_name:
                lines.append(f"Activity display name (draft): {draft.display_name}")
            if draft.description:
                lines.append(f"Activity description (draft): {draft.description}")
            if draft.thread_type:
                lines.append(f"Thread type (draft): {draft.thread_type}")
            if draft.module_type:
                lines.append(f"Module type (draft): {draft.module_type}")

        return "\n".join(lines)

    async def _activity_entry(
        self,
        session: AsyncSession,
        *,
        org_id: UUID,
        thread_type: str | None,
        module_type: str | None,
        activity_entry_id: str | None,
    ) -> ActivityLibraryEntry | None:
        if activity_entry_id:
            return await session.get(ActivityLibraryEntry, UUID(activity_entry_id))
        if not thread_type or not module_type:
            return None
        result = await session.execute(
            select(ActivityLibraryEntry).where(
                ActivityLibraryEntry.is_active.is_(True),
                ActivityLibraryEntry.thread_type == thread_type,
                ActivityLibraryEntry.module_type == module_type,
                or_(
                    ActivityLibraryEntry.scope == "platform",
                    ActivityLibraryEntry.org_id == org_id,
                ),
            ),
        )
        entries = list(result.scalars().all())
        if not entries:
            return None
        return min(entries, key=lambda entry: 0 if entry.scope == "platform" else 1)

    async def _instruction_for_level(
        self,
        session: AsyncSession,
        level: InstructionLevel,
        *,
        org_id: UUID,
        thread_type: str | None = None,
        owner_org_id: UUID | None = None,
        user_id: UUID | None = None,
        cluster_id: UUID | None = None,
        task_id: UUID | None = None,
        task_thread_type: str | None = None,
    ) -> str:
        query = select(InstructionSet).where(InstructionSet.level == level)
        if owner_org_id is not None:
            query = query.where(InstructionSet.owner_org_id == owner_org_id)
        if user_id is not None:
            query = query.where(InstructionSet.user_id == user_id)
        if cluster_id is not None:
            query = query.where(InstructionSet.cluster_id == cluster_id)
        if task_id is not None:
            query = query.where(InstructionSet.task_id == task_id)
        if level == InstructionLevel.PLATFORM:
            query = query.where(InstructionSet.org_id == org_id)
        elif level in _ORG_SCOPED_LEVELS:
            query = query.where(InstructionSet.org_id == org_id)

        if level in _TASK_SCOPED_LEVELS:
            effective_thread_type = task_thread_type
        else:
            effective_thread_type = thread_type
        if effective_thread_type is None:
            query = query.where(InstructionSet.thread_type.is_(None))
        else:
            query = query.where(
                (InstructionSet.thread_type.is_(None))
                | (InstructionSet.thread_type == effective_thread_type),
            )

        result = await session.execute(query.limit(1))
        instruction_set = result.scalar_one_or_none()
        if instruction_set is None or instruction_set.active_version_id is None:
            return ""
        version = await session.get(InstructionVersion, instruction_set.active_version_id)
        return version.content if version is not None else ""


@dataclass
class _EntityContext:
    org_id: UUID
    owner_user_id: UUID
    cluster_id: UUID | None
    task_id: UUID | None
    thread_id: UUID | None
    module_type: str | None
    resolved_thread_type: str | None
    task_thread_type_filter: str | None
    entity_title: str | None
