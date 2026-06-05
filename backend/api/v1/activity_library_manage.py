"""Org-scoped ActivityLibrary management."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_org_admin_user
from core.config import settings
from core.logging import get_logger
from models.activity import ActivityLibraryEntry, ActivityPrompt, PromptStage
from models.user import User
from schemas.admin_activity import (
    AdminActivityLibraryDetailResponse,
    AdminActivityLibraryEntryResponse,
    AdminActivityPromptResponse,
    CreateActivityLibraryEntryRequest,
    ReplaceActivityPromptsRequest,
    UpdateActivityLibraryEntryRequest,
)
from services.activity.instruction_sync import sync_instruction_set_from_activity_default
from services.instructions.integrity_gate import require_activity_default_integrity_approval

logger = get_logger(__name__)

router = APIRouter(prefix="/activity-library/manage", tags=["activity-library-manage"])

_ALLOWED_MODULE_TYPES = frozenset({"external_paper_review", "student_paper_review"})


async def _prompt_count(db: AsyncSession, entry_id: UUID) -> int:
    count = await db.scalar(
        select(func.count())
        .select_from(ActivityPrompt)
        .where(ActivityPrompt.activity_entry_id == entry_id),
    )
    return int(count or 0)


def _entry_response(
    entry: ActivityLibraryEntry,
    *,
    prompt_count: int,
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
        prompt_count=prompt_count,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


async def _get_org_entry(
    db: AsyncSession,
    entry_id: UUID,
    org_id: UUID,
) -> ActivityLibraryEntry:
    result = await db.execute(
        select(ActivityLibraryEntry).where(
            ActivityLibraryEntry.id == entry_id,
            ActivityLibraryEntry.scope == "org",
            ActivityLibraryEntry.org_id == org_id,
        ),
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Activity type not found")
    return entry


def _validate_prompts_for_automation(entry: ActivityLibraryEntry, prompt_count: int) -> None:
    if entry.supports_automation and prompt_count < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Automated activity types require at least one activity prompt",
        )


async def _detail_response(
    db: AsyncSession,
    entry: ActivityLibraryEntry,
) -> AdminActivityLibraryDetailResponse:
    prompts_result = await db.execute(
        select(ActivityPrompt)
        .where(ActivityPrompt.activity_entry_id == entry.id)
        .order_by(ActivityPrompt.sequence_index.asc()),
    )
    prompts = list(prompts_result.scalars().all())
    base = _entry_response(entry, prompt_count=len(prompts))
    return AdminActivityLibraryDetailResponse(
        **base.model_dump(),
        prompts=[
            AdminActivityPromptResponse(
                id=prompt.id,
                prompt_text=prompt.prompt_text,
                stage=prompt.stage.value,
                sequence_index=prompt.sequence_index,
            )
            for prompt in prompts
        ],
    )


@router.get("", response_model=list[AdminActivityLibraryEntryResponse])
async def list_org_activity_library(
    current_user: Annotated[User, Depends(get_org_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    module_type: Annotated[str | None, Query()] = None,
    include_inactive: Annotated[bool, Query()] = False,
) -> list[AdminActivityLibraryEntryResponse]:
    """List org-scoped activity types for the current organization."""
    query = select(ActivityLibraryEntry).where(
        ActivityLibraryEntry.scope == "org",
        ActivityLibraryEntry.org_id == current_user.org_id,
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
        count = await _prompt_count(db, entry.id)
        responses.append(_entry_response(entry, prompt_count=count))

    logger.info(
        "org_activity_library_listed",
        org_id=str(current_user.org_id),
        count=len(responses),
    )
    return responses


@router.get("/{entry_id}", response_model=AdminActivityLibraryDetailResponse)
async def get_org_activity_library_entry(
    entry_id: UUID,
    current_user: Annotated[User, Depends(get_org_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminActivityLibraryDetailResponse:
    """Get org activity type with prompts."""
    entry = await _get_org_entry(db, entry_id, current_user.org_id)
    return await _detail_response(db, entry)


@router.post(
    "",
    response_model=AdminActivityLibraryDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_org_activity_library_entry(
    body: CreateActivityLibraryEntryRequest,
    current_user: Annotated[User, Depends(get_org_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminActivityLibraryDetailResponse:
    """Create an org-scoped activity type (may shadow platform slug for this org)."""
    if body.module_type not in _ALLOWED_MODULE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"module_type must be one of: {', '.join(sorted(_ALLOWED_MODULE_TYPES))}",
        )

    existing = await db.execute(
        select(ActivityLibraryEntry.id).where(
            ActivityLibraryEntry.thread_type == body.thread_type,
            ActivityLibraryEntry.module_type == body.module_type,
            ActivityLibraryEntry.scope == "org",
            ActivityLibraryEntry.org_id == current_user.org_id,
        ),
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Activity type already exists for this organization and module",
        )

    require_activity_default_integrity_approval(
        user_id=str(current_user.id),
        level="org",
        thread_type=body.thread_type,
        module_type=body.module_type,
        entry_id=None,
        content=body.default_instruction_content,
        token=body.integrity_approval_token,
    )

    entry = ActivityLibraryEntry(
        org_id=current_user.org_id,
        thread_type=body.thread_type,
        module_type=body.module_type,
        display_name=body.display_name,
        description=body.description,
        scope="org",
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

    if entry.default_instruction_content:
        await sync_instruction_set_from_activity_default(
            db,
            entry=entry,
            content=entry.default_instruction_content,
            user_id=current_user.id,
        )

    logger.info(
        "org_activity_library_created",
        entry_id=str(entry.id),
        thread_type=entry.thread_type,
        org_id=str(current_user.org_id),
        user_id=str(current_user.id),
    )
    return await _detail_response(db, entry)


@router.patch("/{entry_id}", response_model=AdminActivityLibraryDetailResponse)
async def update_org_activity_library_entry(
    entry_id: UUID,
    body: UpdateActivityLibraryEntryRequest,
    current_user: Annotated[User, Depends(get_org_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminActivityLibraryDetailResponse:
    """Update an org-scoped activity type."""
    entry = await _get_org_entry(db, entry_id, current_user.org_id)
    updates = body.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(entry, field, value)

    if entry.supports_automation:
        count = await _prompt_count(db, entry.id)
        _validate_prompts_for_automation(entry, count)

    if "default_instruction_content" in updates:
        require_activity_default_integrity_approval(
            user_id=str(current_user.id),
            level="org",
            thread_type=entry.thread_type,
            module_type=entry.module_type,
            entry_id=str(entry.id),
            content=entry.default_instruction_content,
            token=body.integrity_approval_token,
        )
        await sync_instruction_set_from_activity_default(
            db,
            entry=entry,
            content=entry.default_instruction_content,
            user_id=current_user.id,
        )

    await db.flush()
    logger.info(
        "org_activity_library_updated",
        entry_id=str(entry_id),
        org_id=str(current_user.org_id),
        user_id=str(current_user.id),
    )
    return await _detail_response(db, entry)


@router.put("/{entry_id}/prompts", response_model=AdminActivityLibraryDetailResponse)
async def replace_org_activity_prompts(
    entry_id: UUID,
    body: ReplaceActivityPromptsRequest,
    current_user: Annotated[User, Depends(get_org_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminActivityLibraryDetailResponse:
    """Replace all activity prompts for an org activity type."""
    entry = await _get_org_entry(db, entry_id, current_user.org_id)
    _validate_prompts_for_automation(entry, len(body.prompts))

    await db.execute(
        delete(ActivityPrompt).where(
            ActivityPrompt.activity_entry_id == entry.id,
        ),
    )

    for index, item in enumerate(body.prompts):
        db.add(
            ActivityPrompt(
                activity_entry_id=entry.id,
                prompt_text=item.prompt_text.strip(),
                stage=PromptStage.OPENING,
                sequence_index=index,
            ),
        )

    await db.flush()
    logger.info(
        "org_activity_library_prompts_replaced",
        entry_id=str(entry_id),
        prompt_count=len(body.prompts),
        user_id=str(current_user.id),
    )
    return await _detail_response(db, entry)
