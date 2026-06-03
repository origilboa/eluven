"""Cluster API endpoints (data model Section 10.3)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.access import get_owned_cluster
from api.deps import get_current_active_user, get_db
from api.kb_queries import collection_document_count
from core.cluster_types import (
    MODULE_STUDENT_PAPER_REVIEW,
    is_assignment_cluster,
)
from core.logging import get_logger
from models.cluster import Cluster
from models.kb import KBCollection, KBCollectionAttachment
from models.task import Task, TaskStatus
from models.thread import Thread
from models.user import User
from schemas.clusters import (
    ClusterResponse,
    CreateClusterRequest,
    CreateSubmissionRequest,
    UpdateClusterRequest,
)
from schemas.kb import ClusterReferenceCollectionResponse
from schemas.tasks import TaskResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/clusters", tags=["clusters"])


async def _task_count(session: AsyncSession, cluster_id: UUID) -> int:
    count = await session.scalar(
        select(func.count()).select_from(Task).where(Task.cluster_id == cluster_id),
    )
    return int(count or 0)


async def _thread_count(session: AsyncSession, task_id: UUID) -> int:
    count = await session.scalar(
        select(func.count()).select_from(Thread).where(Thread.task_id == task_id),
    )
    return int(count or 0)


def _cluster_response(cluster: Cluster, task_count: int) -> ClusterResponse:
    return ClusterResponse(
        id=cluster.id,
        name=cluster.name,
        cluster_type=cluster.cluster_type,
        description=cluster.description,
        working_language=cluster.working_language,
        task_count=task_count,
        created_at=cluster.created_at,
    )


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


@router.get("", response_model=list[ClusterResponse])
async def list_clusters(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ClusterResponse]:
    """List the current user's clusters."""
    result = await db.execute(
        select(Cluster)
        .where(
            Cluster.org_id == current_user.org_id,
            Cluster.owner_id == current_user.id,
        )
        .order_by(Cluster.updated_at.desc()),
    )
    clusters = list(result.scalars().all())

    responses: list[ClusterResponse] = []
    for cluster in clusters:
        count = await _task_count(db, cluster.id)
        responses.append(_cluster_response(cluster, count))

    logger.info("clusters_listed", user_id=str(current_user.id), count=len(responses))
    return responses


@router.post("", response_model=ClusterResponse, status_code=status.HTTP_201_CREATED)
async def create_cluster(
    body: CreateClusterRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClusterResponse:
    """Create a new cluster."""
    if body.cluster_type == MODULE_STUDENT_PAPER_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use cluster_type 'assignment' for Student Paper Review Assignments",
        )

    working_language = body.working_language or current_user.default_working_language
    cluster = Cluster(
        org_id=current_user.org_id,
        owner_id=current_user.id,
        name=body.name,
        cluster_type=body.cluster_type,
        description=body.description,
        working_language=working_language,
    )
    db.add(cluster)
    await db.flush()

    logger.info(
        "cluster_created",
        cluster_id=str(cluster.id),
        cluster_type=cluster.cluster_type,
        user_id=str(current_user.id),
    )
    return _cluster_response(cluster, task_count=0)


@router.get("/{cluster_id}", response_model=ClusterResponse)
async def get_cluster(
    cluster_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClusterResponse:
    """Get cluster detail with task count."""
    cluster = await get_owned_cluster(db, cluster_id, current_user)
    count = await _task_count(db, cluster.id)
    return _cluster_response(cluster, count)


@router.patch("/{cluster_id}", response_model=ClusterResponse)
async def update_cluster(
    cluster_id: UUID,
    body: UpdateClusterRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClusterResponse:
    """Update cluster name, description, or working language."""
    cluster = await get_owned_cluster(db, cluster_id, current_user)

    if body.name is not None:
        cluster.name = body.name
    if body.description is not None:
        cluster.description = body.description
    if body.working_language is not None:
        cluster.working_language = body.working_language

    await db.flush()
    logger.info("cluster_updated", cluster_id=str(cluster_id))
    count = await _task_count(db, cluster.id)
    return _cluster_response(cluster, count)


@router.get(
    "/{cluster_id}/reference-collections",
    response_model=list[ClusterReferenceCollectionResponse],
)
async def list_cluster_reference_collections(
    cluster_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ClusterReferenceCollectionResponse]:
    """List KB collections attached directly to this cluster (reference material)."""
    await get_owned_cluster(db, cluster_id, current_user)

    attachment_result = await db.execute(
        select(KBCollectionAttachment, KBCollection)
        .join(KBCollection, KBCollectionAttachment.collection_id == KBCollection.id)
        .where(
            KBCollectionAttachment.entity_type == "cluster",
            KBCollectionAttachment.entity_id == cluster_id,
            KBCollection.org_id == current_user.org_id,
        )
        .order_by(KBCollection.name.asc()),
    )

    responses: list[ClusterReferenceCollectionResponse] = []
    for attachment, collection in attachment_result.all():
        doc_count = await collection_document_count(db, collection.id)
        responses.append(
            ClusterReferenceCollectionResponse(
                id=collection.id,
                attachment_id=attachment.id,
                name=collection.name,
                description=collection.description,
                document_count=doc_count,
                created_at=collection.created_at,
            ),
        )

    logger.info(
        "cluster_reference_collections_listed",
        cluster_id=str(cluster_id),
        count=len(responses),
    )
    return responses


@router.get("/{cluster_id}/tasks", response_model=list[TaskResponse])
async def list_cluster_tasks(
    cluster_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TaskResponse]:
    """List tasks belonging to a cluster."""
    await get_owned_cluster(db, cluster_id, current_user)

    result = await db.execute(
        select(Task)
        .where(
            Task.cluster_id == cluster_id,
            Task.org_id == current_user.org_id,
            Task.owner_id == current_user.id,
        )
        .order_by(Task.updated_at.desc()),
    )
    tasks = list(result.scalars().all())

    responses: list[TaskResponse] = []
    for task in tasks:
        thread_count = await _thread_count(db, task.id)
        responses.append(_task_response(task, thread_count))

    logger.info(
        "cluster_tasks_listed",
        cluster_id=str(cluster_id),
        count=len(responses),
    )
    return responses


@router.get("/{cluster_id}/submissions", response_model=list[TaskResponse])
async def list_cluster_submissions(
    cluster_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TaskResponse]:
    """List Submission Tasks for an Assignment Cluster."""
    cluster = await get_owned_cluster(db, cluster_id, current_user)
    if not is_assignment_cluster(cluster.cluster_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cluster is not an Assignment",
        )
    return await list_cluster_tasks(cluster_id, current_user, db)


@router.post(
    "/{cluster_id}/submissions",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_submission(
    cluster_id: UUID,
    body: CreateSubmissionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskResponse:
    """Create a Submission Task under an Assignment Cluster."""
    cluster = await get_owned_cluster(db, cluster_id, current_user)
    if not is_assignment_cluster(cluster.cluster_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cluster is not an Assignment",
        )

    working_language = (
        body.working_language
        or cluster.working_language
        or current_user.default_working_language
    )
    task = Task(
        org_id=current_user.org_id,
        owner_id=current_user.id,
        cluster_id=cluster.id,
        title=body.title,
        module_type=MODULE_STUDENT_PAPER_REVIEW,
        status=TaskStatus.DRAFT,
        working_language=working_language,
        context=body.context,
    )
    db.add(task)
    await db.flush()

    logger.info(
        "submission_created",
        cluster_id=str(cluster_id),
        task_id=str(task.id),
        user_id=str(current_user.id),
    )
    thread_count = await _thread_count(db, task.id)
    return _task_response(task, thread_count)
