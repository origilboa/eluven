"""Thread API endpoints (data model Section 10.4)."""

from __future__ import annotations

import json
import mimetypes
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.access import get_owned_task, get_owned_thread
from api.deps import get_current_active_user, get_db
from core.config import settings
from core.database import AsyncSessionLocal
from core.logging import get_logger
from models.activity import ActivityLibraryEntry, ThreadQAQuestion, ThreadQAResponse
from models.kb import KBDocumentStatus, ThreadDocument, ThreadDocumentLoadStrategy
from models.task import Task
from models.thread import MessageRole, Thread, ThreadMessage
from models.user import User
from schemas.threads import (
    CreateThreadRequest,
    DocumentDownloadUrlResponse,
    MessageResponse,
    QAQuestionResponse,
    SendMessageRequest,
    StreamRequest,
    SubmitQARequest,
    ThreadDocumentResponse,
    ThreadResponse,
    UpdateThreadRequest,
)
from services.ai.client import AIClient
from services.ai.context import ContextAssembler
from services.document.constants import SUPPORTED_FILE_TYPES
from services.document_queue import enqueue_document_processing
from services.instructions.thread_instructions import create_thread_instruction_set
from services.storage import StorageService

logger = get_logger(__name__)

router = APIRouter(tags=["threads"])

_SCOPE_PRIORITY = {"org": 0, "user": 1, "platform": 2}


def _thread_response(thread: Thread) -> ThreadResponse:
    return ThreadResponse(
        id=thread.id,
        task_id=thread.task_id,
        title=thread.title,
        thread_type=thread.thread_type,
        status=thread.status.value,
        working_language=thread.working_language,
        is_automated=thread.is_automated,
        token_budget=thread.token_budget,
        tokens_used=thread.tokens_used,
        created_at=thread.created_at,
    )


def _message_response(message: ThreadMessage) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        role=message.role.value,
        content=message.content,
        is_compaction_summary=message.is_compaction_summary,
        input_tokens=message.input_tokens,
        output_tokens=message.output_tokens,
        cached_tokens=message.cached_tokens,
        model_id=message.model_id,
        created_at=message.created_at,
    )


def _thread_document_response(document: ThreadDocument) -> ThreadDocumentResponse:
    return ThreadDocumentResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        size_bytes=document.size_bytes,
        status=document.status.value,
        load_strategy=document.load_strategy.value,
        token_count=document.token_count,
        created_at=document.created_at,
    )


async def _get_owned_thread_document(
    session: AsyncSession,
    *,
    thread_id: UUID,
    document_id: UUID,
    user: User,
) -> tuple[Thread, ThreadDocument]:
    thread = await get_owned_thread(session, thread_id, user)
    document = await session.get(ThreadDocument, document_id)
    if document is None or document.thread_id != thread.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return thread, document


def _file_type_from_filename(filename: str) -> str:
    if "." not in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must include an extension",
        )
    extension = filename.rsplit(".", 1)[-1].lower()
    if extension not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {extension}",
        )
    return extension


def _content_type_for_file_type(file_type: str, filename: str) -> str:
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


async def _activity_entry_for_thread(
    session: AsyncSession,
    *,
    org_id: UUID,
    thread_type: str,
    module_type: str,
) -> ActivityLibraryEntry | None:
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
    return min(entries, key=lambda entry: _SCOPE_PRIORITY.get(entry.scope, 99))


async def _default_thread_title(
    session: AsyncSession,
    *,
    org_id: UUID,
    thread_type: str,
    module_type: str,
    task_title: str,
) -> str:
    entry = await _activity_entry_for_thread(
        session,
        org_id=org_id,
        thread_type=thread_type,
        module_type=module_type,
    )
    label = entry.display_name if entry is not None else thread_type
    return f"{label} — {task_title}"


def _budget_warning(thread: Thread, activity: ActivityLibraryEntry | None) -> bool:
    if thread.token_budget is None or thread.token_budget <= 0:
        return False
    threshold = (
        activity.token_budget_warning_threshold
        if activity is not None
        else 0.8
    )
    return (thread.tokens_used / thread.token_budget) >= threshold


def _sse_line(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


@router.get("/tasks/{task_id}/threads", response_model=list[ThreadResponse])
async def list_threads(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ThreadResponse]:
    """List threads for a task."""
    await get_owned_task(db, task_id, current_user)
    result = await db.execute(
        select(Thread)
        .where(Thread.task_id == task_id, Thread.org_id == current_user.org_id)
        .order_by(Thread.created_at.desc()),
    )
    threads = list(result.scalars().all())
    logger.info("threads_listed", task_id=str(task_id), count=len(threads))
    return [_thread_response(thread) for thread in threads]


@router.post(
    "/tasks/{task_id}/threads",
    response_model=ThreadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_thread(
    task_id: UUID,
    body: CreateThreadRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ThreadResponse:
    """Create a thread; auto-generate title when not provided."""
    task = await get_owned_task(db, task_id, current_user)

    title = body.title
    if not title:
        title = await _default_thread_title(
            db,
            org_id=current_user.org_id,
            thread_type=body.thread_type,
            module_type=task.module_type,
            task_title=task.title,
        )

    activity = await _activity_entry_for_thread(
        db,
        org_id=current_user.org_id,
        thread_type=body.thread_type,
        module_type=task.module_type,
    )

    thread = Thread(
        org_id=current_user.org_id,
        task_id=task.id,
        owner_id=current_user.id,
        title=title,
        thread_type=body.thread_type,
        working_language=body.working_language or task.working_language,
        token_budget=activity.token_budget if activity is not None else None,
    )
    db.add(thread)
    await db.flush()

    await create_thread_instruction_set(
        db,
        thread=thread,
        org_id=current_user.org_id,
        created_by=current_user.id,
        activity=activity,
    )

    logger.info(
        "thread_opened",
        thread_id=str(thread.id),
        task_id=str(task_id),
        thread_type=thread.thread_type,
    )
    return _thread_response(thread)


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ThreadResponse:
    """Get thread detail."""
    thread = await get_owned_thread(db, thread_id, current_user)
    return _thread_response(thread)


@router.patch("/threads/{thread_id}", response_model=ThreadResponse)
async def update_thread(
    thread_id: UUID,
    body: UpdateThreadRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ThreadResponse:
    """Update thread title."""
    thread = await get_owned_thread(db, thread_id, current_user)
    thread.title = body.title
    await db.flush()
    logger.info("thread_updated", thread_id=str(thread_id))
    return _thread_response(thread)


@router.post(
    "/threads/{thread_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    thread_id: UUID,
    body: SendMessageRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Save a user message without triggering AI."""
    thread = await get_owned_thread(db, thread_id, current_user)
    message = ThreadMessage(
        thread_id=thread.id,
        role=MessageRole.USER,
        content=body.content,
    )
    db.add(message)
    await db.flush()
    logger.info("thread_message_saved", thread_id=str(thread_id), message_id=str(message.id))
    return _message_response(message)


@router.get("/threads/{thread_id}/messages", response_model=list[MessageResponse])
async def list_messages(
    thread_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MessageResponse]:
    """Return thread message history."""
    await get_owned_thread(db, thread_id, current_user)
    result = await db.execute(
        select(ThreadMessage)
        .where(ThreadMessage.thread_id == thread_id)
        .order_by(ThreadMessage.created_at.asc()),
    )
    messages = list(result.scalars().all())
    return [_message_response(message) for message in messages]


@router.post("/threads/{thread_id}/stream")
async def stream_ai_response(
    thread_id: UUID,
    body: StreamRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    """Stream AI response via Server-Sent Events."""
    thread = await get_owned_thread(db, thread_id, current_user)
    task = await db.get(Task, thread.task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    activity = await _activity_entry_for_thread(
        db,
        org_id=current_user.org_id,
        thread_type=thread.thread_type,
        module_type=task.module_type,
    )
    budget_warn = _budget_warning(thread, activity)
    content = body.content

    async def event_generator() -> AsyncIterator[str]:
        async with AsyncSessionLocal() as session:
            try:
                stream_thread = await session.get(Thread, thread_id)
                stream_task = await session.get(Task, task.id)
                if stream_thread is None or stream_task is None:
                    yield _sse_line({"type": "error", "message": "Thread not found"})
                    return

                yield _sse_line({"type": "status", "message": "Preparing response..."})

                assembler = ContextAssembler()
                client = AIClient()

                if await assembler.will_compact(session, thread_id):
                    yield _sse_line(
                        {
                            "type": "status",
                            "message": "Summarising earlier conversation...",
                        },
                    )

                async for chunk in client.stream(
                    stream_thread,
                    stream_task,
                    content,
                    session,
                    budget_warning=budget_warn,
                ):
                    if isinstance(chunk, str):
                        yield _sse_line({"type": "text", "text": chunk})
                        continue
                    event_type = chunk.get("type")
                    if event_type == "memory_entry":
                        yield _sse_line(
                            {
                                "type": "memory_entry",
                                "entry": chunk.get("entry", {}),
                            },
                        )
                    elif event_type == "done":
                        yield _sse_line(
                            {
                                "type": "done",
                                "input_tokens": chunk.get("input_tokens", 0),
                                "output_tokens": chunk.get("output_tokens", 0),
                                "cached_tokens": chunk.get("cached_tokens", 0),
                            },
                        )
                await session.commit()
            except Exception as exc:
                await session.rollback()
                logger.warning(
                    "thread_stream_failed",
                    thread_id=str(thread_id),
                    error=str(exc),
                )
                yield _sse_line({"type": "error", "message": str(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/threads/{thread_id}/documents",
    response_model=ThreadDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_thread_document(
    thread_id: UUID,
    file: UploadFile,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ThreadDocumentResponse:
    """Upload a document to a thread and enqueue for processing.

    Deprecated: upload papers via POST /tasks/{task_id}/documents instead.
    """
    thread = await get_owned_thread(db, thread_id, current_user)

    filename = file.filename or "document"
    file_type = _file_type_from_filename(filename)
    file_bytes = await file.read()
    size_bytes = len(file_bytes)

    document_id = uuid4()
    s3_key = f"{current_user.org_id}/threads/{thread_id}/{document_id}/{filename}"
    content_type = _content_type_for_file_type(file_type, filename)

    document = ThreadDocument(
        id=document_id,
        thread_id=thread.id,
        filename=filename,
        s3_key=s3_key,
        size_bytes=size_bytes,
        file_type=file_type,
        load_strategy=ThreadDocumentLoadStrategy.FULL_TEXT,
        status=KBDocumentStatus.PENDING,
        uploaded_by=current_user.id,
    )
    db.add(document)
    await db.flush()

    storage = StorageService()
    storage.upload_file(file_bytes, s3_key, content_type)

    logger.info(
        "thread_document_upload",
        thread_id=str(thread_id),
        document_id=str(document_id),
        file_type=file_type,
        size_bytes=size_bytes,
    )

    enqueue_document_processing(document_id, "thread")
    return _thread_document_response(document)


@router.get(
    "/threads/{thread_id}/documents",
    response_model=list[ThreadDocumentResponse],
)
async def list_thread_documents(
    thread_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ThreadDocumentResponse]:
    """List documents attached to a thread (manuscript / submission files)."""
    await get_owned_thread(db, thread_id, current_user)
    result = await db.execute(
        select(ThreadDocument)
        .where(ThreadDocument.thread_id == thread_id)
        .order_by(ThreadDocument.created_at.desc()),
    )
    documents = list(result.scalars().all())
    logger.info(
        "thread_documents_listed",
        thread_id=str(thread_id),
        count=len(documents),
    )
    return [_thread_document_response(document) for document in documents]


@router.get(
    "/threads/{thread_id}/documents/{document_id}/download-url",
    response_model=DocumentDownloadUrlResponse,
)
async def get_thread_document_download_url(
    thread_id: UUID,
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentDownloadUrlResponse:
    """Return a presigned URL to download a thread document."""
    _thread, document = await _get_owned_thread_document(
        db,
        thread_id=thread_id,
        document_id=document_id,
        user=current_user,
    )
    storage = StorageService()
    url = storage.generate_presigned_url(document.s3_key)
    expires_in = settings.s3_presigned_url_expiry_seconds
    logger.info(
        "thread_document_download_url_issued",
        thread_id=str(thread_id),
        document_id=str(document_id),
    )
    return DocumentDownloadUrlResponse(
        url=url,
        filename=document.filename,
        expires_in_seconds=expires_in,
    )


@router.get("/threads/{thread_id}/qa", response_model=list[QAQuestionResponse])
async def get_thread_qa(
    thread_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[QAQuestionResponse]:
    """Return Q&A questions for the thread's activity type with any existing answers."""
    thread = await get_owned_thread(db, thread_id, current_user)
    task = await db.get(Task, thread.task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    activity = await _activity_entry_for_thread(
        db,
        org_id=current_user.org_id,
        thread_type=thread.thread_type,
        module_type=task.module_type,
    )
    if activity is None:
        return []

    questions_result = await db.execute(
        select(ThreadQAQuestion)
        .where(ThreadQAQuestion.activity_entry_id == activity.id)
        .order_by(ThreadQAQuestion.sequence_index.asc()),
    )
    questions = list(questions_result.scalars().all())

    responses_result = await db.execute(
        select(ThreadQAResponse).where(ThreadQAResponse.thread_id == thread.id),
    )
    responses = list(responses_result.scalars().all())
    latest_by_question: dict[UUID, ThreadQAResponse] = {}
    for response in responses:
        latest_by_question[response.question_id] = response

    results: list[QAQuestionResponse] = []
    for question in questions:
        existing = latest_by_question.get(question.id)
        results.append(
            QAQuestionResponse(
                id=question.id,
                question_text=question.question_text,
                stage=question.stage.value,
                response_type=question.response_type.value,
                options=question.options,
                is_required=question.is_required,
                sequence_index=question.sequence_index,
                response_text=existing.response_text if existing else None,
                response_options=existing.response_options if existing else None,
                responded_at=existing.responded_at if existing else None,
            ),
        )
    return results


@router.post("/threads/{thread_id}/qa", response_model=list[QAQuestionResponse])
async def submit_thread_qa(
    thread_id: UUID,
    body: SubmitQARequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[QAQuestionResponse]:
    """Submit Q&A responses for a thread."""
    thread = await get_owned_thread(db, thread_id, current_user)
    task = await db.get(Task, thread.task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    activity = await _activity_entry_for_thread(
        db,
        org_id=current_user.org_id,
        thread_type=thread.thread_type,
        module_type=task.module_type,
    )
    if activity is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No activity library entry for this thread type",
        )

    question_rows = await db.execute(
        select(ThreadQAQuestion.id).where(
            ThreadQAQuestion.activity_entry_id == activity.id,
        ),
    )
    valid_question_ids = set(question_rows.scalars().all())

    for item in body.responses:
        if item.question_id not in valid_question_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid question_id: {item.question_id}",
            )
        if not item.response_text and not item.response_options:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each response must include response_text or response_options",
            )

        await db.execute(
            delete(ThreadQAResponse).where(
                ThreadQAResponse.thread_id == thread.id,
                ThreadQAResponse.question_id == item.question_id,
            ),
        )
        db.add(
            ThreadQAResponse(
                thread_id=thread.id,
                question_id=item.question_id,
                response_text=item.response_text,
                response_options=item.response_options,
            ),
        )

    await db.flush()
    logger.info(
        "thread_qa_submitted",
        thread_id=str(thread_id),
        response_count=len(body.responses),
    )
    return await get_thread_qa(thread_id, current_user, db)
