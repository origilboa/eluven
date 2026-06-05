"""Instruction layer API endpoints (data model Section 10.7)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.access import get_owned_cluster, get_owned_task, get_owned_thread
from api.deps import get_current_active_user, get_db
from core.config import settings
from core.logging import get_logger
from models.instruction import InstructionLevel, InstructionSet, InstructionVersion
from models.user import User, UserRole
from schemas.instruction_assistant import (
    InstructionAssistantStreamRequest,
    InstructionIntegrityCheckRequest,
    InstructionIntegrityRemediateRequest,
)
from schemas.instructions import (
    ActivateInstructionVersionRequest,
    CreateInstructionVersionRequest,
    InstructionSetResponse,
    InstructionVersionResponse,
)
from services.instructions.authoring_assistant import InstructionAuthoringAssistant
from services.instructions.integrity_checker import InstructionIntegrityChecker
from services.instructions.integrity_gate import (
    require_instruction_integrity_approval,
    scope_key_from_instruction_set,
)
from services.instructions.integrity_remediator import InstructionIntegrityRemediator

logger = get_logger(__name__)

router = APIRouter(prefix="/instructions", tags=["instructions"])

STUDIO_LEVELS = frozenset(
    {
        InstructionLevel.PLATFORM.value,
        InstructionLevel.ORG.value,
        InstructionLevel.USER.value,
    },
)


def _parse_studio_level(level: str) -> InstructionLevel:
    if level not in STUDIO_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported instruction level: {level}",
        )
    return InstructionLevel(level)


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


async def _studio_instruction_set_query(
    level: InstructionLevel,
    user: User,
):
    query = select(InstructionSet).where(
        InstructionSet.level == level,
        InstructionSet.thread_type.is_(None),
    )
    if level == InstructionLevel.PLATFORM:
        query = query.where(InstructionSet.org_id == user.org_id)
    elif level == InstructionLevel.ORG:
        query = query.where(InstructionSet.owner_org_id == user.org_id)
    else:
        query = query.where(
            InstructionSet.org_id == user.org_id,
            InstructionSet.user_id == user.id,
        )
    return query


async def _entity_instruction_set_query(
    *,
    level: InstructionLevel,
    org_id: UUID,
    cluster_id: UUID | None = None,
    task_id: UUID | None = None,
    thread_id: UUID | None = None,
    thread_type: str | None = None,
):
    query = select(InstructionSet).where(
        InstructionSet.level == level,
        InstructionSet.org_id == org_id,
    )
    if cluster_id is not None:
        query = query.where(InstructionSet.cluster_id == cluster_id)
    if task_id is not None:
        query = query.where(InstructionSet.task_id == task_id)
    if thread_id is not None:
        query = query.where(InstructionSet.thread_id == thread_id)
    if thread_type is None:
        query = query.where(InstructionSet.thread_type.is_(None))
    else:
        query = query.where(InstructionSet.thread_type == thread_type)
    return query


async def _get_or_create_studio_instruction_set(
    session: AsyncSession,
    level: InstructionLevel,
    user: User,
) -> InstructionSet:
    query = await _studio_instruction_set_query(level, user)
    result = await session.execute(query.limit(1))
    instruction_set = result.scalar_one_or_none()
    if instruction_set is not None:
        return instruction_set

    instruction_set = InstructionSet(
        org_id=user.org_id,
        level=level,
        owner_org_id=user.org_id if level == InstructionLevel.ORG else None,
        user_id=user.id if level == InstructionLevel.USER else None,
    )
    session.add(instruction_set)
    await session.flush()
    return instruction_set


async def _get_or_create_entity_instruction_set(
    session: AsyncSession,
    *,
    level: InstructionLevel,
    user: User,
    cluster_id: UUID | None = None,
    task_id: UUID | None = None,
    thread_id: UUID | None = None,
    thread_type: str | None = None,
) -> InstructionSet:
    query = await _entity_instruction_set_query(
        level=level,
        org_id=user.org_id,
        cluster_id=cluster_id,
        task_id=task_id,
        thread_id=thread_id,
        thread_type=thread_type,
    )
    result = await session.execute(query.limit(1))
    instruction_set = result.scalar_one_or_none()
    if instruction_set is not None:
        return instruction_set

    instruction_set = InstructionSet(
        org_id=user.org_id,
        level=level,
        cluster_id=cluster_id,
        task_id=task_id,
        thread_id=thread_id,
        thread_type=thread_type,
    )
    session.add(instruction_set)
    await session.flush()
    return instruction_set


async def _get_entity_instruction_set(
    session: AsyncSession,
    *,
    level: InstructionLevel,
    org_id: UUID,
    cluster_id: UUID | None = None,
    task_id: UUID | None = None,
    thread_id: UUID | None = None,
    thread_type: str | None = None,
) -> InstructionSet | None:
    query = await _entity_instruction_set_query(
        level=level,
        org_id=org_id,
        cluster_id=cluster_id,
        task_id=task_id,
        thread_id=thread_id,
        thread_type=thread_type,
    )
    result = await session.execute(query.limit(1))
    return result.scalar_one_or_none()


def _version_response(
    version: InstructionVersion,
    *,
    is_active: bool,
) -> InstructionVersionResponse:
    return InstructionVersionResponse(
        id=version.id,
        version_number=version.version_number,
        content=version.content,
        change_note=version.change_note,
        created_by=version.created_by,
        created_at=version.created_at,
        is_active=is_active,
    )


async def _instruction_set_response(
    session: AsyncSession,
    instruction_set: InstructionSet,
) -> InstructionSetResponse:
    result = await session.execute(
        select(InstructionVersion)
        .where(InstructionVersion.instruction_set_id == instruction_set.id)
        .order_by(InstructionVersion.version_number.desc()),
    )
    versions = list(result.scalars().all())
    active_id = instruction_set.active_version_id

    version_responses = [
        _version_response(version, is_active=version.id == active_id) for version in versions
    ]
    active_version = next((item for item in version_responses if item.is_active), None)

    return InstructionSetResponse(
        id=instruction_set.id,
        level=instruction_set.level.value,
        thread_type=instruction_set.thread_type,
        cluster_id=instruction_set.cluster_id,
        task_id=instruction_set.task_id,
        thread_id=instruction_set.thread_id,
        active_version=active_version,
        versions=version_responses,
    )


async def _create_instruction_version(
    session: AsyncSession,
    *,
    instruction_set: InstructionSet,
    body: CreateInstructionVersionRequest,
    user: User,
    log_context: dict[str, str],
) -> InstructionSetResponse:
    require_instruction_integrity_approval(
        user_id=str(user.id),
        scope_key=scope_key_from_instruction_set(instruction_set),
        content=body.content,
        token=body.integrity_approval_token,
    )
    logger.info(
        "instruction_integrity_gate_passed",
        user_id=str(user.id),
        **log_context,
    )
    max_version = await session.scalar(
        select(func.max(InstructionVersion.version_number)).where(
            InstructionVersion.instruction_set_id == instruction_set.id,
        ),
    )
    next_version = int(max_version or 0) + 1

    version = InstructionVersion(
        instruction_set_id=instruction_set.id,
        version_number=next_version,
        content=body.content,
        change_note=body.change_note,
        created_by=user.id,
    )
    session.add(version)
    await session.flush()

    if instruction_set.active_version_id is None:
        instruction_set.active_version_id = version.id

    logger.info(
        "instruction_version_created",
        version_id=str(version.id),
        version_number=next_version,
        user_id=str(user.id),
        **log_context,
    )
    return await _instruction_set_response(session, instruction_set)


# --- Cluster instructions (level 4) ---


@router.get("/clusters/{cluster_id}", response_model=InstructionSetResponse)
async def get_cluster_instruction_set(
    cluster_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    thread_type: Annotated[str | None, Query()] = None,
) -> InstructionSetResponse:
    """Get cluster-level instruction set and version history."""
    await get_owned_cluster(db, cluster_id, current_user)
    instruction_set = await _get_or_create_entity_instruction_set(
        db,
        level=InstructionLevel.CLUSTER,
        user=current_user,
        cluster_id=cluster_id,
        thread_type=thread_type,
    )
    logger.info(
        "cluster_instruction_set_retrieved",
        cluster_id=str(cluster_id),
        thread_type=thread_type,
        user_id=str(current_user.id),
    )
    return await _instruction_set_response(db, instruction_set)


@router.post(
    "/clusters/{cluster_id}",
    response_model=InstructionSetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cluster_instruction_version(
    cluster_id: UUID,
    body: CreateInstructionVersionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    thread_type: Annotated[str | None, Query()] = None,
) -> InstructionSetResponse:
    """Create a new cluster-level instruction version."""
    await get_owned_cluster(db, cluster_id, current_user)
    instruction_set = await _get_or_create_entity_instruction_set(
        db,
        level=InstructionLevel.CLUSTER,
        user=current_user,
        cluster_id=cluster_id,
        thread_type=thread_type,
    )
    return await _create_instruction_version(
        db,
        instruction_set=instruction_set,
        body=body,
        user=current_user,
        log_context={
            "level": InstructionLevel.CLUSTER.value,
            "cluster_id": str(cluster_id),
            "thread_type": thread_type or "",
        },
    )


@router.post("/clusters/{cluster_id}/activate", response_model=InstructionSetResponse)
async def activate_cluster_instruction_version(
    cluster_id: UUID,
    body: ActivateInstructionVersionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    thread_type: Annotated[str | None, Query()] = None,
) -> InstructionSetResponse:
    """Promote a cluster instruction version to active."""
    await get_owned_cluster(db, cluster_id, current_user)
    instruction_set = await _get_entity_instruction_set(
        db,
        level=InstructionLevel.CLUSTER,
        org_id=current_user.org_id,
        cluster_id=cluster_id,
        thread_type=thread_type,
    )
    if instruction_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instruction set not found",
        )

    version = await db.get(InstructionVersion, body.version_id)
    if version is None or version.instruction_set_id != instruction_set.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instruction version not found",
        )

    instruction_set.active_version_id = version.id
    logger.info(
        "cluster_instruction_version_activated",
        cluster_id=str(cluster_id),
        thread_type=thread_type,
        version_id=str(version.id),
        user_id=str(current_user.id),
    )
    return await _instruction_set_response(db, instruction_set)


# --- Task instructions (level 5 — task-wide InstructionSet) ---


@router.get("/tasks/{task_id}", response_model=InstructionSetResponse)
async def get_task_instruction_set(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    thread_type: Annotated[str | None, Query()] = None,
) -> InstructionSetResponse:
    """Get task-level instruction set and version history."""
    await get_owned_task(db, task_id, current_user)
    instruction_set = await _get_or_create_entity_instruction_set(
        db,
        level=InstructionLevel.TASK,
        user=current_user,
        task_id=task_id,
        thread_type=thread_type,
    )
    logger.info(
        "task_instruction_set_retrieved",
        task_id=str(task_id),
        thread_type=thread_type,
        user_id=str(current_user.id),
    )
    return await _instruction_set_response(db, instruction_set)


@router.post(
    "/tasks/{task_id}",
    response_model=InstructionSetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task_instruction_version(
    task_id: UUID,
    body: CreateInstructionVersionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    thread_type: Annotated[str | None, Query()] = None,
) -> InstructionSetResponse:
    """Create a new task-level instruction version."""
    await get_owned_task(db, task_id, current_user)
    instruction_set = await _get_or_create_entity_instruction_set(
        db,
        level=InstructionLevel.TASK,
        user=current_user,
        task_id=task_id,
        thread_type=thread_type,
    )
    return await _create_instruction_version(
        db,
        instruction_set=instruction_set,
        body=body,
        user=current_user,
        log_context={
            "level": InstructionLevel.TASK.value,
            "task_id": str(task_id),
            "thread_type": thread_type or "",
        },
    )


@router.post("/tasks/{task_id}/activate", response_model=InstructionSetResponse)
async def activate_task_instruction_version(
    task_id: UUID,
    body: ActivateInstructionVersionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    thread_type: Annotated[str | None, Query()] = None,
) -> InstructionSetResponse:
    """Promote a task instruction version to active."""
    await get_owned_task(db, task_id, current_user)
    instruction_set = await _get_entity_instruction_set(
        db,
        level=InstructionLevel.TASK,
        org_id=current_user.org_id,
        task_id=task_id,
        thread_type=thread_type,
    )
    if instruction_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instruction set not found",
        )

    version = await db.get(InstructionVersion, body.version_id)
    if version is None or version.instruction_set_id != instruction_set.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instruction version not found",
        )

    instruction_set.active_version_id = version.id
    logger.info(
        "task_instruction_version_activated",
        task_id=str(task_id),
        thread_type=thread_type,
        version_id=str(version.id),
        user_id=str(current_user.id),
    )
    return await _instruction_set_response(db, instruction_set)


# --- Thread instructions (per-thread instance) ---


@router.get("/threads/{thread_id}", response_model=InstructionSetResponse)
async def get_thread_instruction_set(
    thread_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InstructionSetResponse:
    """Get thread-level instruction set and version history."""
    await get_owned_thread(db, thread_id, current_user)
    instruction_set = await _get_or_create_entity_instruction_set(
        db,
        level=InstructionLevel.THREAD,
        user=current_user,
        thread_id=thread_id,
    )
    logger.info(
        "thread_instruction_set_retrieved",
        thread_id=str(thread_id),
        user_id=str(current_user.id),
    )
    return await _instruction_set_response(db, instruction_set)


@router.post(
    "/threads/{thread_id}",
    response_model=InstructionSetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_thread_instruction_version(
    thread_id: UUID,
    body: CreateInstructionVersionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InstructionSetResponse:
    """Create a new thread-level instruction version."""
    await get_owned_thread(db, thread_id, current_user)
    instruction_set = await _get_or_create_entity_instruction_set(
        db,
        level=InstructionLevel.THREAD,
        user=current_user,
        thread_id=thread_id,
    )
    return await _create_instruction_version(
        db,
        instruction_set=instruction_set,
        body=body,
        user=current_user,
        log_context={
            "level": InstructionLevel.THREAD.value,
            "thread_id": str(thread_id),
        },
    )


@router.post("/threads/{thread_id}/activate", response_model=InstructionSetResponse)
async def activate_thread_instruction_version(
    thread_id: UUID,
    body: ActivateInstructionVersionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InstructionSetResponse:
    """Promote a thread instruction version to active."""
    await get_owned_thread(db, thread_id, current_user)
    instruction_set = await _get_entity_instruction_set(
        db,
        level=InstructionLevel.THREAD,
        org_id=current_user.org_id,
        thread_id=thread_id,
    )
    if instruction_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instruction set not found",
        )

    version = await db.get(InstructionVersion, body.version_id)
    if version is None or version.instruction_set_id != instruction_set.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instruction version not found",
        )

    instruction_set.active_version_id = version.id
    logger.info(
        "thread_instruction_version_activated",
        thread_id=str(thread_id),
        version_id=str(version.id),
        user_id=str(current_user.id),
    )
    return await _instruction_set_response(db, instruction_set)


# --- Instruction authoring assistant ---


def _instruction_assistant_sse_line(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


@router.post("/assistant/integrity-check")
async def check_instruction_integrity(
    body: InstructionIntegrityCheckRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Structured integrity check; returns approval token on pass."""
    checker = InstructionIntegrityChecker()
    return await checker.check(
        db,
        user=current_user,
        scope=body.scope,
        draft_content=body.draft_content,
        locale=body.locale,
    )


@router.post("/assistant/integrity-check/remediate")
async def remediate_instruction_integrity(
    body: InstructionIntegrityRemediateRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Stream remediation guidance after a failed integrity check."""
    if not body.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one chat message is required",
        )

    remediator = InstructionIntegrityRemediator()

    async def event_generator() -> AsyncIterator[str]:
        try:
            yield _instruction_assistant_sse_line(
                {"type": "status", "message": "Preparing remediation..."},
            )
            async for chunk in remediator.stream(db, user=current_user, request=body):
                if isinstance(chunk, str):
                    yield _instruction_assistant_sse_line({"type": "text", "text": chunk})
                    continue
                if chunk.get("type") == "done":
                    yield _instruction_assistant_sse_line(
                        {
                            "type": "done",
                            "input_tokens": chunk.get("input_tokens", 0),
                            "output_tokens": chunk.get("output_tokens", 0),
                            "cached_tokens": chunk.get("cached_tokens", 0),
                        },
                    )
        except Exception as exc:
            logger.warning(
                "instruction_integrity_remediate_failed",
                user_id=str(current_user.id),
                error=str(exc),
            )
            yield _instruction_assistant_sse_line({"type": "error", "message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/assistant/stream")
async def stream_instruction_authoring_assistant(
    body: InstructionAssistantStreamRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Stream instruction authoring assistant responses via SSE."""
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

    assistant = InstructionAuthoringAssistant()

    async def event_generator() -> AsyncIterator[str]:
        try:
            yield _instruction_assistant_sse_line(
                {"type": "status", "message": "Preparing response..."},
            )
            async for chunk in assistant.stream(db, user=current_user, request=body):
                if isinstance(chunk, str):
                    yield _instruction_assistant_sse_line({"type": "text", "text": chunk})
                    continue
                if chunk.get("type") == "done":
                    yield _instruction_assistant_sse_line(
                        {
                            "type": "done",
                            "input_tokens": chunk.get("input_tokens", 0),
                            "output_tokens": chunk.get("output_tokens", 0),
                            "cached_tokens": chunk.get("cached_tokens", 0),
                        },
                    )
        except HTTPException as exc:
            yield _instruction_assistant_sse_line(
                {"type": "error", "message": str(exc.detail)},
            )
        except Exception as exc:
            logger.warning(
                "instruction_authoring_stream_failed",
                user_id=str(current_user.id),
                level=body.scope.level,
                error=str(exc),
            )
            yield _instruction_assistant_sse_line({"type": "error", "message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# --- Instruction Studio levels 1–3 ---


@router.get("/{level}", response_model=InstructionSetResponse)
async def get_instruction_set(
    level: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InstructionSetResponse:
    """Get instruction set and version history for a hierarchy level."""
    parsed_level = _parse_studio_level(level)

    instruction_set = await _get_or_create_studio_instruction_set(db, parsed_level, current_user)
    logger.info(
        "instruction_set_retrieved",
        level=parsed_level.value,
        user_id=str(current_user.id),
    )
    return await _instruction_set_response(db, instruction_set)


@router.post("/{level}", response_model=InstructionSetResponse, status_code=status.HTTP_201_CREATED)
async def create_instruction_version(
    level: str,
    body: CreateInstructionVersionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InstructionSetResponse:
    """Create a new instruction version at the given level."""
    parsed_level = _parse_studio_level(level)
    _require_studio_level_write(parsed_level, current_user)

    instruction_set = await _get_or_create_studio_instruction_set(db, parsed_level, current_user)
    return await _create_instruction_version(
        db,
        instruction_set=instruction_set,
        body=body,
        user=current_user,
        log_context={"level": parsed_level.value},
    )


@router.post("/{level}/activate", response_model=InstructionSetResponse)
async def activate_instruction_version(
    level: str,
    body: ActivateInstructionVersionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InstructionSetResponse:
    """Promote an instruction version to active for new tasks."""
    parsed_level = _parse_studio_level(level)
    _require_studio_level_write(parsed_level, current_user)

    query = await _studio_instruction_set_query(parsed_level, current_user)
    result = await db.execute(query.limit(1))
    instruction_set = result.scalar_one_or_none()
    if instruction_set is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instruction set not found",
        )

    version = await db.get(InstructionVersion, body.version_id)
    if version is None or version.instruction_set_id != instruction_set.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instruction version not found",
        )

    instruction_set.active_version_id = version.id

    logger.info(
        "instruction_version_activated",
        level=parsed_level.value,
        version_id=str(version.id),
        user_id=str(current_user.id),
    )
    return await _instruction_set_response(db, instruction_set)
