"""Workflow API endpoints (data model Section 10.6)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.access import get_owned_task
from api.deps import get_current_active_user, get_db
from api.document_helpers import raise_if_integrity_blocked
from core.logging import get_logger
from models.task import Task
from models.user import User
from models.workflow import (
    WorkflowExecution,
    WorkflowIntervention,
    WorkflowTemplate,
    WorkflowThreadExecution,
)
from schemas.workflows import (
    InterventionResponseRequest,
    StartWorkflowRequest,
    WorkflowExecutionResponse,
    WorkflowInterventionResponse,
    WorkflowTemplateResponse,
    WorkflowThreadExecutionResponse,
)
from services.workflow.engine import WorkflowEngine, WorkflowEngineError
from services.document.integrity_gate import evaluate_task_integrity_gate

logger = get_logger(__name__)

router = APIRouter(tags=["workflows"])

PLATFORM_ORG_ID = UUID("00000000-0000-0000-0000-000000000001")


def _template_response(template: WorkflowTemplate) -> WorkflowTemplateResponse:
    return WorkflowTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        module_type=template.module_type,
        scope=template.scope,
        thread_sequence=list(template.thread_sequence),
        created_at=template.created_at,
    )


def _thread_execution_response(
    row: WorkflowThreadExecution,
) -> WorkflowThreadExecutionResponse:
    return WorkflowThreadExecutionResponse(
        id=row.id,
        thread_type=row.thread_type,
        sequence_index=row.sequence_index,
        status=row.status.value,
        thread_id=row.thread_id,
        retry_count=row.retry_count,
        error=row.error,
        started_at=row.started_at,
        completed_at=row.completed_at,
    )


def _intervention_response(row: WorkflowIntervention) -> WorkflowInterventionResponse:
    return WorkflowInterventionResponse(
        id=row.id,
        workflow_thread_execution_id=row.workflow_thread_execution_id,
        trigger_type=row.trigger_type.value,
        question=row.question,
        user_response=row.user_response,
        triggered_at=row.triggered_at,
        responded_at=row.responded_at,
    )


async def _execution_response(
    session: AsyncSession,
    execution: WorkflowExecution,
) -> WorkflowExecutionResponse:
    thread_result = await session.execute(
        select(WorkflowThreadExecution)
        .where(WorkflowThreadExecution.workflow_execution_id == execution.id)
        .order_by(WorkflowThreadExecution.sequence_index.asc()),
    )
    thread_executions = list(thread_result.scalars().all())

    intervention_result = await session.execute(
        select(WorkflowIntervention)
        .where(WorkflowIntervention.workflow_execution_id == execution.id)
        .order_by(WorkflowIntervention.triggered_at.asc()),
    )
    interventions = list(intervention_result.scalars().all())

    return WorkflowExecutionResponse(
        id=execution.id,
        task_id=execution.task_id,
        status=execution.status.value,
        current_thread_index=execution.current_thread_index,
        total_threads=execution.total_threads,
        total_tokens_used=execution.total_tokens_used,
        thread_executions=[_thread_execution_response(row) for row in thread_executions],
        interventions=[_intervention_response(row) for row in interventions],
        started_at=execution.started_at,
        completed_at=execution.completed_at,
    )


async def _get_owned_execution(
    session: AsyncSession,
    execution_id: UUID,
    user: User,
) -> WorkflowExecution:
    execution = await session.get(WorkflowExecution, execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow execution not found",
        )
    task = await session.get(Task, execution.task_id)
    if task is None or task.org_id != user.org_id or task.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow execution not found",
        )
    return execution


@router.get("/workflow-templates", response_model=list[WorkflowTemplateResponse])
async def list_workflow_templates(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[WorkflowTemplateResponse]:
    """List workflow templates available to the current user."""
    result = await db.execute(
        select(WorkflowTemplate)
        .where(
            or_(
                WorkflowTemplate.org_id == current_user.org_id,
                and_(
                    WorkflowTemplate.org_id == PLATFORM_ORG_ID,
                    WorkflowTemplate.scope == "platform",
                ),
            ),
        )
        .order_by(WorkflowTemplate.name.asc()),
    )
    templates = list(result.scalars().all())
    logger.info(
        "workflow_templates_listed",
        user_id=str(current_user.id),
        count=len(templates),
    )
    return [_template_response(template) for template in templates]


@router.post(
    "/tasks/{task_id}/workflows",
    response_model=WorkflowExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_workflow(
    task_id: UUID,
    body: StartWorkflowRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowExecutionResponse:
    """Start a workflow execution for a task."""
    await get_owned_task(db, task_id, current_user)

    gate = await evaluate_task_integrity_gate(db, task_id)
    raise_if_integrity_blocked(gate)

    template = await db.get(WorkflowTemplate, body.template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow template not found",
        )
    if template.org_id not in (current_user.org_id, PLATFORM_ORG_ID):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow template not found",
        )

    engine = WorkflowEngine()
    try:
        execution_id = await engine.start(
            task_id=task_id,
            template_id=body.template_id,
            triggered_by_user_id=current_user.id,
            session=db,
        )
    except WorkflowEngineError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    execution = await db.get(WorkflowExecution, execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Workflow execution could not be loaded",
        )

    return await _execution_response(db, execution)


@router.get(
    "/tasks/{task_id}/workflows/{execution_id}",
    response_model=WorkflowExecutionResponse,
)
async def get_workflow_execution(
    task_id: UUID,
    execution_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowExecutionResponse:
    """Get workflow execution status."""
    await get_owned_task(db, task_id, current_user)
    execution = await _get_owned_execution(db, execution_id, current_user)
    if execution.task_id != task_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow execution not found",
        )
    return await _execution_response(db, execution)


@router.post(
    "/workflows/{execution_id}/interventions/{intervention_id}/respond",
    response_model=WorkflowExecutionResponse,
)
async def respond_to_intervention(
    execution_id: UUID,
    intervention_id: UUID,
    body: InterventionResponseRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> WorkflowExecutionResponse:
    """Respond to a paused workflow intervention and resume execution."""
    execution = await _get_owned_execution(db, execution_id, current_user)

    intervention = await db.get(WorkflowIntervention, intervention_id)
    if intervention is None or intervention.workflow_execution_id != execution.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intervention not found",
        )

    engine = WorkflowEngine()
    try:
        await engine.resume(
            workflow_execution_id=execution.id,
            intervention_id=intervention.id,
            user_response=body.response,
            session=db,
        )
    except WorkflowEngineError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    await db.refresh(execution)
    return await _execution_response(db, execution)
