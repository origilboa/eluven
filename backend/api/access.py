"""Shared resource ownership checks for API routes."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from models.cluster import Cluster
from models.task import Task
from models.thread import Thread
from models.user import User


async def get_owned_cluster(
    session: AsyncSession,
    cluster_id: UUID,
    user: User,
) -> Cluster:
    """Load a cluster owned by the current user or raise 404."""
    cluster = await session.get(Cluster, cluster_id)
    if cluster is None or cluster.org_id != user.org_id or cluster.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cluster not found")
    return cluster


async def get_owned_task(
    session: AsyncSession,
    task_id: UUID,
    user: User,
) -> Task:
    """Load a task owned by the current user or raise 404."""
    task = await session.get(Task, task_id)
    if task is None or task.org_id != user.org_id or task.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


async def get_owned_thread(
    session: AsyncSession,
    thread_id: UUID,
    user: User,
) -> Thread:
    """Load a thread owned by the current user or raise 404."""
    thread = await session.get(Thread, thread_id)
    if thread is None or thread.org_id != user.org_id or thread.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return thread
