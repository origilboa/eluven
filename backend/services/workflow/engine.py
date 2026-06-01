"""Workflow execution engine — orchestrates automated thread sequences."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import settings
from core.logging import get_logger
from models.activity import ActivityLibraryEntry
from models.task import Task
from models.thread import Thread, ThreadStatus
from models.workflow import (
    WorkflowExecution,
    WorkflowIntervention,
    WorkflowStatus,
    WorkflowTemplate,
    WorkflowThreadExecution,
    WorkflowThreadStatus,
)
from schemas.task_memory import TaskMemoryEntryPayload
from services.ai.client import AIClient
from services.workflow.interventions import DetectedIntervention, detect_intervention
from services.workflow.queue import enqueue_workflow_thread

logger = get_logger(__name__)

PLATFORM_ORG_ID = UUID("00000000-0000-0000-0000-000000000001")

_DEFAULT_AUTOMATION_MESSAGE = (
    "Execute this automated workflow step. Follow your instructions, write structured "
    "task memory where appropriate, and if you cannot proceed safely emit a fenced "
    "intervention block:\n"
    '```intervention\n{"trigger_type": "<type>", "question": "<your question>"}\n```\n'
    "Valid trigger_type values: missing_document, explicit_ambiguity, "
    "confidence_below_threshold, conflicting_information."
)


class WorkflowEngineError(Exception):
    """Raised when workflow operations cannot proceed."""


class WorkflowEngine:
    """Start, execute, and resume automated multi-thread workflows."""

    def __init__(self, ai_client: AIClient | None = None) -> None:
        self._ai_client = ai_client or AIClient()

    async def start(
        self,
        task_id: UUID,
        template_id: UUID,
        triggered_by_user_id: UUID,
        session: AsyncSession,
    ) -> UUID:
        """Create a workflow execution and enqueue the first thread step."""
        task = await session.get(Task, task_id)
        if task is None:
            raise WorkflowEngineError(f"Task not found: {task_id}")

        template = await session.get(WorkflowTemplate, template_id)
        if template is None:
            raise WorkflowEngineError(f"Workflow template not found: {template_id}")

        if not template.thread_sequence:
            raise WorkflowEngineError("Workflow template has an empty thread_sequence")

        execution = WorkflowExecution(
            org_id=task.org_id,
            task_id=task.id,
            template_id=template.id,
            triggered_by=triggered_by_user_id,
            status=WorkflowStatus.RUNNING,
            current_thread_index=0,
            total_threads=len(template.thread_sequence),
        )
        session.add(execution)
        await session.flush()

        first_thread_execution_id: UUID | None = None
        for index, thread_type in enumerate(template.thread_sequence):
            thread_execution = WorkflowThreadExecution(
                workflow_execution_id=execution.id,
                thread_type=thread_type,
                sequence_index=index,
                status=WorkflowThreadStatus.PENDING,
            )
            session.add(thread_execution)
            await session.flush()
            if index == 0:
                first_thread_execution_id = thread_execution.id

        if first_thread_execution_id is None:
            raise WorkflowEngineError("Failed to create workflow thread executions")

        enqueue_workflow_thread(execution.id, first_thread_execution_id)

        logger.info(
            "workflow_started",
            workflow_id=str(execution.id),
            task_id=str(task.id),
            thread_count=execution.total_threads,
            template_id=str(template.id),
        )
        return execution.id

    async def execute_thread(
        self,
        workflow_execution_id: UUID,
        thread_execution_id: UUID,
        session: AsyncSession,
    ) -> None:
        """Run a single workflow thread step (with retries on failure)."""
        execution = await self._load_execution(session, workflow_execution_id)
        if execution.status not in (WorkflowStatus.RUNNING,):
            logger.info(
                "workflow_thread_skipped",
                workflow_id=str(workflow_execution_id),
                thread_execution_id=str(thread_execution_id),
                status=execution.status.value,
            )
            return

        thread_execution = await self._get_thread_execution(
            session,
            workflow_execution_id,
            thread_execution_id,
        )
        if thread_execution.status == WorkflowThreadStatus.COMPLETE:
            logger.info(
                "workflow_thread_already_complete",
                workflow_id=str(workflow_execution_id),
                thread_execution_id=str(thread_execution_id),
            )
            return

        max_retries = settings.workflow_max_retries
        last_error: Exception | None = None

        for attempt in range(max_retries):
            try:
                await self._execute_thread_once(
                    session=session,
                    execution=execution,
                    thread_execution=thread_execution,
                )
                return
            except Exception as exc:
                last_error = exc
                thread_execution.retry_count += 1
                thread_execution.error = str(exc)
                thread_execution.status = WorkflowThreadStatus.FAILED
                await session.flush()

                logger.warning(
                    "workflow_thread_attempt_failed",
                    workflow_id=str(workflow_execution_id),
                    thread_execution_id=str(thread_execution_id),
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(exc),
                )

                if thread_execution.retry_count >= max_retries:
                    break

                thread_execution.status = WorkflowThreadStatus.PENDING
                await session.flush()
                await asyncio.sleep(2**attempt)

        execution.status = WorkflowStatus.FAILED
        execution.failed_at = datetime.now(UTC)
        await session.flush()

        logger.warning(
            "workflow_failed",
            workflow_id=str(workflow_execution_id),
            thread_execution_id=str(thread_execution_id),
            error=str(last_error) if last_error else "unknown",
        )
        raise WorkflowEngineError(
            f"Workflow thread failed after {max_retries} attempts: {last_error}",
        ) from last_error

    async def resume(
        self,
        workflow_execution_id: UUID,
        intervention_id: UUID,
        user_response: str,
        session: AsyncSession,
    ) -> None:
        """Save an intervention response and re-enqueue the paused thread step."""
        execution = await self._load_execution(session, workflow_execution_id)
        if execution.status != WorkflowStatus.PAUSED:
            raise WorkflowEngineError("Workflow is not paused for intervention")

        intervention = await session.get(WorkflowIntervention, intervention_id)
        if intervention is None or intervention.workflow_execution_id != execution.id:
            raise WorkflowEngineError(f"Intervention not found: {intervention_id}")

        if intervention.user_response is not None:
            raise WorkflowEngineError("Intervention has already been answered")

        intervention.user_response = user_response
        intervention.responded_at = datetime.now(UTC)
        execution.status = WorkflowStatus.RUNNING
        await session.flush()

        enqueue_workflow_thread(execution.id, intervention.workflow_thread_execution_id)

        logger.info(
            "workflow_resumed",
            workflow_id=str(workflow_execution_id),
            intervention_id=str(intervention_id),
            thread_execution_id=str(intervention.workflow_thread_execution_id),
        )

    async def _execute_thread_once(
        self,
        *,
        session: AsyncSession,
        execution: WorkflowExecution,
        thread_execution: WorkflowThreadExecution,
    ) -> None:
        task = await session.get(Task, execution.task_id)
        if task is None:
            raise WorkflowEngineError(f"Task not found for workflow: {execution.id}")

        thread_execution.status = WorkflowThreadStatus.RUNNING
        thread_execution.started_at = datetime.now(UTC)
        thread_execution.error = None
        await session.flush()

        thread = await self._resolve_thread(session, execution, thread_execution, task)
        activity = await self._activity_entry(session, task, thread_execution.thread_type)
        intervention_response = await self._answered_intervention_response(
            session,
            thread_execution.id,
        )
        message = self._automation_message(activity, intervention_response)

        memory_payloads: list[TaskMemoryEntryPayload] = []
        tokens_used = 0

        async for chunk in self._ai_client.stream(
            thread,
            task,
            message,
            session,
            workflow_id=execution.id,
        ):
            if isinstance(chunk, dict):
                if chunk.get("type") == "done":
                    tokens_used = int(chunk.get("input_tokens", 0)) + int(
                        chunk.get("output_tokens", 0),
                    )
                elif chunk.get("type") == "memory_entry":
                    entry_data = chunk.get("entry", {})
                    try:
                        entry_type = entry_data.get("entry_type") or entry_data.get("type")
                        content = entry_data.get("content")
                        if entry_type and content:
                            memory_payloads.append(
                                TaskMemoryEntryPayload.model_validate(
                                    {
                                        "type": entry_type,
                                        "content": content,
                                        "confidence": entry_data.get("confidence"),
                                    },
                                ),
                            )
                    except Exception:
                        pass

        await session.refresh(thread)
        assistant_text = await self._latest_assistant_content(session, thread.id)
        detected = detect_intervention(
            assistant_text,
            memory_payloads=memory_payloads,
        )

        if detected is not None:
            await self._pause_for_intervention(
                session=session,
                execution=execution,
                thread_execution=thread_execution,
                detected=detected,
            )
            return

        await self._complete_thread_step(
            session=session,
            execution=execution,
            thread_execution=thread_execution,
            thread=thread,
            tokens_used=tokens_used,
        )

    async def _pause_for_intervention(
        self,
        *,
        session: AsyncSession,
        execution: WorkflowExecution,
        thread_execution: WorkflowThreadExecution,
        detected: DetectedIntervention,
    ) -> None:
        intervention = WorkflowIntervention(
            workflow_execution_id=execution.id,
            workflow_thread_execution_id=thread_execution.id,
            trigger_type=detected.trigger_type,
            question=detected.question,
        )
        session.add(intervention)
        execution.status = WorkflowStatus.PAUSED
        thread_execution.status = WorkflowThreadStatus.RUNNING
        await session.flush()

        logger.info(
            "workflow_intervention",
            workflow_id=str(execution.id),
            trigger_type=detected.trigger_type.value,
            thread_type=thread_execution.thread_type,
            thread_execution_id=str(thread_execution.id),
        )

    async def _complete_thread_step(
        self,
        *,
        session: AsyncSession,
        execution: WorkflowExecution,
        thread_execution: WorkflowThreadExecution,
        thread: Thread,
        tokens_used: int,
    ) -> None:
        thread_execution.status = WorkflowThreadStatus.COMPLETE
        thread_execution.completed_at = datetime.now(UTC)
        thread.status = ThreadStatus.COMPLETE
        thread.completed_at = datetime.now(UTC)
        execution.current_thread_index = thread_execution.sequence_index + 1
        execution.total_tokens_used += tokens_used
        await session.flush()

        memory_written = await self._count_memory_for_thread(session, thread.id)

        logger.info(
            "workflow_thread_complete",
            workflow_id=str(execution.id),
            thread_type=thread_execution.thread_type,
            thread_execution_id=str(thread_execution.id),
            memory_entries_written=memory_written,
        )

        next_step = await self._next_pending_thread(session, execution.id)
        if next_step is not None:
            enqueue_workflow_thread(execution.id, next_step.id)
            return

        execution.status = WorkflowStatus.COMPLETE
        execution.completed_at = datetime.now(UTC)
        await session.flush()

        logger.info(
            "workflow_complete",
            workflow_id=str(execution.id),
            total_threads=execution.total_threads,
            total_tokens=execution.total_tokens_used,
        )

    async def _resolve_thread(
        self,
        session: AsyncSession,
        execution: WorkflowExecution,
        thread_execution: WorkflowThreadExecution,
        task: Task,
    ) -> Thread:
        if thread_execution.thread_id is not None:
            thread = await session.get(Thread, thread_execution.thread_id)
            if thread is not None:
                return thread

        activity = await self._activity_entry(session, task, thread_execution.thread_type)
        display_name = (
            activity.display_name if activity is not None else thread_execution.thread_type
        )
        title = f"{display_name} — {task.title} (automated)"

        thread = Thread(
            org_id=task.org_id,
            task_id=task.id,
            owner_id=execution.triggered_by,
            title=title,
            thread_type=thread_execution.thread_type,
            working_language=task.working_language,
            is_automated=True,
            status=ThreadStatus.ACTIVE,
            token_budget=activity.token_budget if activity is not None else None,
        )
        session.add(thread)
        await session.flush()

        thread_execution.thread_id = thread.id
        await session.flush()
        return thread

    def _automation_message(
        self,
        activity: ActivityLibraryEntry | None,
        intervention_response: str | None,
    ) -> str:
        base_message = _DEFAULT_AUTOMATION_MESSAGE
        if activity is not None and activity.automation_execution_spec:
            spec = activity.automation_execution_spec
            prompt = spec.get("opening_message") or spec.get("prompt")
            if isinstance(prompt, str) and prompt.strip():
                base_message = prompt.strip()

        if intervention_response:
            return f"{base_message}\n\nUser clarification:\n{intervention_response}"

        return base_message

    async def _answered_intervention_response(
        self,
        session: AsyncSession,
        thread_execution_id: UUID,
    ) -> str | None:
        result = await session.execute(
            select(WorkflowIntervention)
            .where(
                WorkflowIntervention.workflow_thread_execution_id == thread_execution_id,
                WorkflowIntervention.user_response.is_not(None),
            )
            .order_by(WorkflowIntervention.responded_at.desc())
            .limit(1),
        )
        intervention = result.scalar_one_or_none()
        return intervention.user_response if intervention is not None else None

    async def _load_execution(
        self,
        session: AsyncSession,
        workflow_execution_id: UUID,
    ) -> WorkflowExecution:
        execution = await session.get(WorkflowExecution, workflow_execution_id)
        if execution is None:
            raise WorkflowEngineError(f"Workflow execution not found: {workflow_execution_id}")
        return execution

    async def _get_thread_execution(
        self,
        session: AsyncSession,
        workflow_execution_id: UUID,
        thread_execution_id: UUID,
    ) -> WorkflowThreadExecution:
        thread_execution = await session.get(WorkflowThreadExecution, thread_execution_id)
        if (
            thread_execution is None
            or thread_execution.workflow_execution_id != workflow_execution_id
        ):
            raise WorkflowEngineError(f"Thread execution not found: {thread_execution_id}")
        return thread_execution

    async def _next_pending_thread(
        self,
        session: AsyncSession,
        workflow_execution_id: UUID,
    ) -> WorkflowThreadExecution | None:
        result = await session.execute(
            select(WorkflowThreadExecution)
            .where(
                WorkflowThreadExecution.workflow_execution_id == workflow_execution_id,
                WorkflowThreadExecution.status == WorkflowThreadStatus.PENDING,
            )
            .order_by(WorkflowThreadExecution.sequence_index.asc())
            .limit(1),
        )
        return result.scalar_one_or_none()

    async def _activity_entry(
        self,
        session: AsyncSession,
        task: Task,
        thread_type: str,
    ) -> ActivityLibraryEntry | None:
        result = await session.execute(
            select(ActivityLibraryEntry)
            .where(
                ActivityLibraryEntry.is_active.is_(True),
                ActivityLibraryEntry.thread_type == thread_type,
                ActivityLibraryEntry.module_type == task.module_type,
                or_(
                    ActivityLibraryEntry.scope == "platform",
                    ActivityLibraryEntry.org_id == task.org_id,
                ),
            )
            .limit(1),
        )
        return result.scalar_one_or_none()

    async def _latest_assistant_content(
        self,
        session: AsyncSession,
        thread_id: UUID,
    ) -> str:
        from models.thread import MessageRole, ThreadMessage

        result = await session.execute(
            select(ThreadMessage)
            .where(
                ThreadMessage.thread_id == thread_id,
                ThreadMessage.role == MessageRole.ASSISTANT,
            )
            .order_by(ThreadMessage.created_at.desc())
            .limit(1),
        )
        message = result.scalar_one_or_none()
        return message.content if message is not None else ""

    async def _count_memory_for_thread(self, session: AsyncSession, thread_id: UUID) -> int:
        from models.memory import TaskMemoryEntry

        count_result = await session.execute(
            select(TaskMemoryEntry).where(TaskMemoryEntry.thread_id == thread_id),
        )
        return len(list(count_result.scalars().all()))
