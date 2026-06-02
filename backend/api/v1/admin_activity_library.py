"""Admin ActivityLibrary management (app_admin only)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_app_admin_user, get_db
from core.config import settings
from core.logging import get_logger
from core.platform import PLATFORM_ORG_ID
from models.activity import ActivityLibraryEntry, QAStage, ThreadQAQuestion
from models.user import User
from schemas.admin_activity import (
    AdminActivityLibraryDetailResponse,
    AdminActivityLibraryEntryResponse,
    AdminThreadQAQuestionResponse,
    CreateActivityLibraryEntryRequest,
    ReplaceOpeningQuestionsRequest,
    UpdateActivityLibraryEntryRequest,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/activity-library", tags=["admin-activity-library"])

_ALLOWED_MODULE_TYPES = frozenset({"external_paper_review", "student_paper_review"})


async def _opening_question_count(db: AsyncSession, entry_id: UUID) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(ThreadQAQuestion)
        .where(
            ThreadQAQuestion.activity_entry_id == entry_id,
            ThreadQAQuestion.stage == QAStage.OPENING,
        ),
    )
    return int(count or 0)


def _entry_response(
    entry: ActivityLibraryEntry,
    *,
    opening_question_count: int,
) -> AdminActivityLibraryEntryResponse:
    return AdminActivityLibraryEntryResponse(
        id=entry.id,
        thread_type=entry.thread_type,
        module_type=entry.module_type,
        display_name=entry.display_name,
        description=entry.description,
        scope=entry.scope,
        is_active=entry.is_active,
        default_model_id=entry.default_model_id,
        fallback_model_id=entry.fallback_model_id,
        token_budget=entry.token_budget,
        token_budget_warning_threshold=entry.token_budget_warning_threshold,
        supports_automation=entry.supports_automation,
        default_instruction_content=entry.default_instruction_content,
        opening_question_count=opening_question_count,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


async def _get_platform_entry(db: AsyncSession, entry_id: UUID) -> ActivityLibraryEntry:
    result = await db.execute(
        select(ActivityLibraryEntry).where(
            ActivityLibraryEntry.id == entry_id,
            ActivityLibraryEntry.scope == "platform",
            ActivityLibraryEntry.org_id == PLATFORM_ORG_ID,
        ),
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity type not found")
    return entry


@router.get("", response_model=list[AdminActivityLibraryEntryResponse])
async def list_admin_activity_library(
    _admin: Annotated[User, Depends(get_app_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    module_type: Annotated[str | None, Query()] = None,
    include_inactive: Annotated[bool, Query()] = False,
) -> list[AdminActivityLibraryEntryResponse]:
    """List platform activity types for admin management."""
    query = select(ActivityLibraryEntry).where(
        ActivityLibraryEntry.scope == "platform",
        ActivityLibraryEntry.org_id == PLATFORM_ORG_ID,
    )
    if module_type is not None:
        query = query.where(ActivityLibraryEntry.module_type == module_type)
    if not include_inactive:
        query = query.where(ActivityLibraryEntry.is_active.is_(True))

    query = query.order_by(
        ActivityLibraryEntry.module_type.asc(),
        ActivityLibraryEntry.display_name.asc(),
    )
    result = await db.execute(query)
    entries = list(result.scalars().all())

    responses: list[AdminActivityLibraryEntryResponse] = []
    for entry in entries:
        count = await _opening_question_count(db, entry.id)
        responses.append(_entry_response(entry, opening_question_count=count))

    logger.info(
        "admin_activity_library_listed",
        module_type=module_type,
        include_inactive=include_inactive,
        count=len(responses),
    )
    return responses


@router.get("/{entry_id}", response_model=AdminActivityLibraryDetailResponse)
async def get_admin_activity_library_entry(
    entry_id: UUID,
    _admin: Annotated[User, Depends(get_app_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminActivityLibraryDetailResponse:
    """Get activity type with opening Q&A questions."""
    entry = await _get_platform_entry(db, entry_id)

    questions_result = await db.execute(
        select(ThreadQAQuestion)
        .where(
            ThreadQAQuestion.activity_entry_id == entry.id,
            ThreadQAQuestion.stage == QAStage.OPENING,
        )
        .order_by(ThreadQAQuestion.sequence_index.asc()),
    )
    questions = list(questions_result.scalars().all())

    base = _entry_response(
        entry,
        opening_question_count=len(questions),
    )
    return AdminActivityLibraryDetailResponse(
        **base.model_dump(),
        opening_questions=[
            AdminThreadQAQuestionResponse(
                id=question.id,
                question_text=question.question_text,
                stage=question.stage.value,
                response_type=question.response_type.value,
                options=question.options,
                is_required=question.is_required,
                sequence_index=question.sequence_index,
            )
            for question in questions
        ],
    )


@router.post(
    "",
    response_model=AdminActivityLibraryDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_admin_activity_library_entry(
    body: CreateActivityLibraryEntryRequest,
    admin: Annotated[User, Depends(get_app_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminActivityLibraryDetailResponse:
    """Create a platform activity type."""
    if body.module_type not in _ALLOWED_MODULE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"module_type must be one of: {', '.join(sorted(_ALLOWED_MODULE_TYPES))}",
        )

    existing = await db.execute(
        select(ActivityLibraryEntry.id).where(
            ActivityLibraryEntry.thread_type == body.thread_type,
            ActivityLibraryEntry.module_type == body.module_type,
            ActivityLibraryEntry.scope == "platform",
        ),
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Activity type already exists for this module",
        )

    entry = ActivityLibraryEntry(
        org_id=PLATFORM_ORG_ID,
        thread_type=body.thread_type,
        module_type=body.module_type,
        display_name=body.display_name,
        description=body.description,
        scope="platform",
        is_active=body.is_active,
        default_model_id=body.default_model_id or settings.default_bedrock_model_id,
        fallback_model_id=body.fallback_model_id,
        token_budget=body.token_budget,
        token_budget_warning_threshold=body.token_budget_warning_threshold,
        supports_automation=body.supports_automation,
        default_instruction_content=body.default_instruction_content,
    )
    db.add(entry)
    await db.flush()

    logger.info(
        "admin_activity_library_created",
        entry_id=str(entry.id),
        thread_type=entry.thread_type,
        module_type=entry.module_type,
        user_id=str(admin.id),
    )
    return await get_admin_activity_library_entry(entry.id, admin, db)


@router.patch("/{entry_id}", response_model=AdminActivityLibraryDetailResponse)
async def update_admin_activity_library_entry(
    entry_id: UUID,
    body: UpdateActivityLibraryEntryRequest,
    admin: Annotated[User, Depends(get_app_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminActivityLibraryDetailResponse:
    """Update a platform activity type."""
    entry = await _get_platform_entry(db, entry_id)
    updates = body.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(entry, field, value)

    await db.flush()
    logger.info(
        "admin_activity_library_updated",
        entry_id=str(entry_id),
        fields=list(updates.keys()),
        user_id=str(admin.id),
    )
    return await get_admin_activity_library_entry(entry_id, admin, db)


@router.put("/{entry_id}/opening-questions", response_model=AdminActivityLibraryDetailResponse)
async def replace_opening_questions(
    entry_id: UUID,
    body: ReplaceOpeningQuestionsRequest,
    admin: Annotated[User, Depends(get_app_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminActivityLibraryDetailResponse:
    """Replace all opening Q&A questions for an activity type."""
    entry = await _get_platform_entry(db, entry_id)

    await db.execute(
        delete(ThreadQAQuestion).where(
            ThreadQAQuestion.activity_entry_id == entry.id,
            ThreadQAQuestion.stage == QAStage.OPENING,
        ),
    )

    for index, item in enumerate(body.questions):
        db.add(
            ThreadQAQuestion(
                activity_entry_id=entry.id,
                question_text=item.question_text.strip(),
                stage=QAStage.OPENING,
                is_required=item.is_required,
                sequence_index=index,
            ),
        )

    await db.flush()
    logger.info(
        "admin_activity_library_opening_questions_replaced",
        entry_id=str(entry_id),
        question_count=len(body.questions),
        user_id=str(admin.id),
    )
    return await get_admin_activity_library_entry(entry_id, admin, db)
