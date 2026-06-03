"""ActivityLibrary API endpoints (data model Section 10.8)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user, get_db
from core.logging import get_logger
from models.activity import ActivityLibraryEntry, ActivityPrompt
from models.user import User
from schemas.activity import ActivityLibraryDetailResponse, ActivityLibraryEntryResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/activity-library", tags=["activity-library"])

PLATFORM_ORG_ID = UUID("00000000-0000-0000-0000-000000000001")


def _entry_response(entry: ActivityLibraryEntry) -> ActivityLibraryEntryResponse:
    return ActivityLibraryEntryResponse(
        id=entry.id,
        thread_type=entry.thread_type,
        module_type=entry.module_type,
        display_name=entry.display_name,
        description=entry.description,
        scope=entry.scope,
        default_model_id=entry.default_model_id,
        token_budget=entry.token_budget,
        supports_automation=entry.supports_automation,
    )


@router.get("", response_model=list[ActivityLibraryEntryResponse])
async def list_activity_library(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    module_type: Annotated[str | None, Query()] = None,
) -> list[ActivityLibraryEntryResponse]:
    """List available thread types, optionally filtered by module."""
    query = select(ActivityLibraryEntry).where(
        ActivityLibraryEntry.is_active.is_(True),
        or_(
            ActivityLibraryEntry.scope == "platform",
            ActivityLibraryEntry.org_id == current_user.org_id,
        ),
    )
    if module_type is not None:
        query = query.where(ActivityLibraryEntry.module_type == module_type)

    query = query.order_by(ActivityLibraryEntry.display_name.asc())
    result = await db.execute(query)
    entries = list(result.scalars().all())

    logger.info(
        "activity_library_listed",
        user_id=str(current_user.id),
        module_type=module_type,
        count=len(entries),
    )
    return [_entry_response(entry) for entry in entries]


@router.get("/{thread_type}", response_model=ActivityLibraryDetailResponse)
async def get_activity_library_entry(
    thread_type: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    module_type: Annotated[str | None, Query()] = None,
) -> ActivityLibraryDetailResponse:
    """Get a thread type definition with activity prompt count."""
    query = select(ActivityLibraryEntry).where(
        ActivityLibraryEntry.is_active.is_(True),
        ActivityLibraryEntry.thread_type == thread_type,
        or_(
            ActivityLibraryEntry.scope == "platform",
            ActivityLibraryEntry.org_id == current_user.org_id,
        ),
    )
    if module_type is not None:
        query = query.where(ActivityLibraryEntry.module_type == module_type)

    result = await db.execute(query.limit(1))
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread type not found")

    prompt_count = await db.scalar(
        select(func.count())
        .select_from(ActivityPrompt)
        .where(ActivityPrompt.activity_entry_id == entry.id),
    )

    base = _entry_response(entry)
    return ActivityLibraryDetailResponse(
        **base.model_dump(),
        prompt_count=int(prompt_count or 0),
    )
