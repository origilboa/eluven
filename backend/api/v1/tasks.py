"""Task API endpoints (data model Section 10.2)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.access import get_owned_task
from api.deps import get_current_active_user, get_db
from core.logging import get_logger
from models.cluster import Cluster
from models.memory import TaskMemoryEntry, TaskMemoryEntryType
from models.task import Task, TaskStatus
from models.thread import Thread
from models.user import User
from schemas.tasks import (
    CreateTaskRequest,
    TaskMemoryEntryResponse,
    TaskMemoryResponse,
    TaskResponse,
    UpdateTaskRequest,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def _thread_count(session: AsyncSession, task_id: UUID) -> int:
    count = await session.scalar(
        select(func.count()).select_from(Thread).where(Thread.task_id == task_id),
    )
    return int(count or 0)


def _task_response(task: Task, thread_count: int) -> TaskResponse:
    return TaskResponse(
        id=task.id,
        title=task.title,
        module_type=task.module_type,
        status=task.status.value,
        cluster_id=task.cluster_id,
        working_language=task.working_language,
        context=task.context,
        thread_count=thread_count,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _memory_entry_response(entry: TaskMemoryEntry) -> TaskMemoryEntryResponse:
    return TaskMemoryEntryResponse(
        id=entry.id,
        entry_type=entry.entry_type.value,
        content=entry.content,
        confidence=entry.confidence,
        thread_id=entry.thread_id,
        model_id=entry.model_id,
        is_automated=entry.is_automated,
        created_at=entry.created_at,
    )


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    module_type: Annotated[str | None, Query()] = None,
    cluster_id: Annotated[UUID | None, Query()] = None,
) -> list[TaskResponse]:
    """List the current user's tasks with optional filters."""
    query = select(Task).where(
        Task.org_id == current_user.org_id,
        Task.owner_id == current_user.id,
    )
    if status_filter is not None:
        try:
            status_enum = TaskStatus(status_filter)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}",
            ) from exc
        query = query.where(Task.status == status_enum)
    if module_type is not None:
        query = query.where(Task.module_type == module_type)
    if cluster_id is not None:
        query = query.where(Task.cluster_id == cluster_id)

    query = query.order_by(Task.updated_at.desc())
    result = await db.execute(query)
    tasks = list(result.scalars().all())

    responses: list[TaskResponse] = []
    for task in tasks:
        count = await _thread_count(db, task.id)
        responses.append(_task_response(task, count))

    logger.info("tasks_listed", user_id=str(current_user.id), count=len(responses))
    return responses


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: CreateTaskRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskResponse:
    """Create a new task."""
    if body.cluster_id is not None:
        cluster = await db.get(Cluster, body.cluster_id)
        if (
            cluster is None
            or cluster.org_id != current_user.org_id
            or cluster.owner_id != current_user.id
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found")

    working_language = body.working_language or current_user.default_working_language
    task = Task(
        org_id=current_user.org_id,
        owner_id=current_user.id,
        title=body.title,
        module_type=body.module_type,
        cluster_id=body.cluster_id,
        working_language=working_language,
        context=body.context,
    )
    db.add(task)
    await db.flush()

    logger.info(
        "task_created",
        task_id=str(task.id),
        module_type=task.module_type,
        user_id=str(current_user.id),
    )
    return _task_response(task, thread_count=0)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskResponse:
    """Get task detail."""
    task = await get_owned_task(db, task_id, current_user)
    count = await _thread_count(db, task.id)
    return _task_response(task, count)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    body: UpdateTaskRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskResponse:
    """Update task fields."""
    task = await get_owned_task(db, task_id, current_user)

    if body.cluster_id is not None:
        cluster = await db.get(Cluster, body.cluster_id)
        if (
            cluster is None
            or cluster.org_id != current_user.org_id
            or cluster.owner_id != current_user.id
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found")
        task.cluster_id = body.cluster_id

    if body.title is not None:
        task.title = body.title
    if body.description is not None:
        task.description = body.description
    if body.working_language is not None:
        task.working_language = body.working_language
    if body.context is not None:
        task.context = body.context

    await db.flush()
    logger.info("task_updated", task_id=str(task_id))
    count = await _thread_count(db, task.id)
    return _task_response(task, count)


@router.delete("/{task_id}", response_model=TaskResponse)
async def archive_task(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskResponse:
    """Archive a task (soft delete — status set to archived)."""
    task = await get_owned_task(db, task_id, current_user)
    task.status = TaskStatus.ARCHIVED
    await db.flush()

    logger.info("task_archived", task_id=str(task_id))
    count = await _thread_count(db, task.id)
    return _task_response(task, count)


@router.get("/{task_id}/memory", response_model=TaskMemoryResponse)
async def get_task_memory(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskMemoryResponse:
    """Return task memory entries grouped by type."""
    await get_owned_task(db, task_id, current_user)

    result = await db.execute(
        select(TaskMemoryEntry)
        .where(
            TaskMemoryEntry.task_id == task_id,
            TaskMemoryEntry.is_deleted.is_(False),
        )
        .order_by(TaskMemoryEntry.created_at.asc()),
    )
    entries = list(result.scalars().all())

    grouped: dict[TaskMemoryEntryType, list[TaskMemoryEntryResponse]] = {
        TaskMemoryEntryType.FINDING: [],
        TaskMemoryEntryType.ASSUMPTION: [],
        TaskMemoryEntryType.GAP: [],
        TaskMemoryEntryType.REFERENCE: [],
    }
    for entry in entries:
        grouped[entry.entry_type].append(_memory_entry_response(entry))

    logger.info(
        "task_memory_listed",
        task_id=str(task_id),
        entry_count=len(entries),
    )
    return TaskMemoryResponse(
        findings=grouped[TaskMemoryEntryType.FINDING],
        assumptions=grouped[TaskMemoryEntryType.ASSUMPTION],
        gaps=grouped[TaskMemoryEntryType.GAP],
        references=grouped[TaskMemoryEntryType.REFERENCE],
    )
