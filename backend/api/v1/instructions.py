"""Instruction layer API endpoints (data model Section 10.7)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user, get_db
from core.logging import get_logger
from models.instruction import InstructionLevel, InstructionSet, InstructionVersion
from models.user import User, UserRole
from schemas.instructions import (
    ActivateInstructionVersionRequest,
    CreateInstructionVersionRequest,
    InstructionSetResponse,
    InstructionVersionResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/instructions", tags=["instructions"])

STUDIO_LEVELS = frozenset(
    {
        InstructionLevel.PLATFORM.value,
        InstructionLevel.ORG.value,
        InstructionLevel.USER.value,
    },
)


def _parse_level(level: str) -> InstructionLevel:
    if level not in STUDIO_LEVELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported instruction level: {level}",
        )
    return InstructionLevel(level)


def _require_level_write(level: InstructionLevel, user: User) -> None:
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


async def _instruction_set_query(
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


async def _get_or_create_instruction_set(
    session: AsyncSession,
    level: InstructionLevel,
    user: User,
) -> InstructionSet:
    query = await _instruction_set_query(level, user)
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


async def _get_instruction_set(
    session: AsyncSession,
    level: InstructionLevel,
    user: User,
) -> InstructionSet | None:
    query = await _instruction_set_query(level, user)
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
        active_version=active_version,
        versions=version_responses,
    )


@router.get("/{level}", response_model=InstructionSetResponse)
async def get_instruction_set(
    level: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InstructionSetResponse:
    """Get instruction set and version history for a hierarchy level."""
    parsed_level = _parse_level(level)

    instruction_set = await _get_or_create_instruction_set(db, parsed_level, current_user)
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
    parsed_level = _parse_level(level)
    _require_level_write(parsed_level, current_user)

    instruction_set = await _get_or_create_instruction_set(db, parsed_level, current_user)

    max_version = await db.scalar(
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
        created_by=current_user.id,
    )
    db.add(version)
    await db.flush()

    if instruction_set.active_version_id is None:
        instruction_set.active_version_id = version.id

    logger.info(
        "instruction_version_created",
        level=parsed_level.value,
        version_id=str(version.id),
        version_number=next_version,
        user_id=str(current_user.id),
    )
    return await _instruction_set_response(db, instruction_set)


@router.post("/{level}/activate", response_model=InstructionSetResponse)
async def activate_instruction_version(
    level: str,
    body: ActivateInstructionVersionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> InstructionSetResponse:
    """Promote an instruction version to active for new tasks."""
    parsed_level = _parse_level(level)
    _require_level_write(parsed_level, current_user)

    instruction_set = await _get_instruction_set(db, parsed_level, current_user)
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
