"""Admin API endpoints (Section 10.9)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.admin_access import (
    assert_can_access_org,
    assert_can_assign_role,
    can_manage_user,
    is_app_admin,
    is_platform_org,
)
from api.deps import get_app_admin_user, get_db, get_org_admin_user
from core.config import settings
from core.logging import get_logger
from core.security import get_user_by_email
from models.invitation import UserInvitation
from models.org import Org
from models.user import User, UserRole
from schemas.admin import (
    AdminUserResponse,
    CreateInvitationRequest,
    CreateInvitationResponse,
    CreateOrgRequest,
    InvitationResponse,
    OrgResponse,
    UpdateAdminUserRequest,
    UpdateOrgRequest,
)
from services.invitations import (
    generate_invite_token,
    hash_invite_token,
    invitation_expires_at,
    is_invitation_expired,
    slugify_org_name,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _invitation_status(invitation: UserInvitation) -> str:
    if invitation.revoked_at is not None:
        return "revoked"
    if invitation.accepted_at is not None:
        return "accepted"
    if is_invitation_expired(invitation.expires_at):
        return "expired"
    return "pending"


def _invitation_response(
    invitation: UserInvitation,
    *,
    org_name: str,
    invited_by_name: str,
) -> InvitationResponse:
    return InvitationResponse(
        id=invitation.id,
        org_id=invitation.org_id,
        org_name=org_name,
        email=invitation.email,
        name=invitation.name,
        role=invitation.role.value,
        status=_invitation_status(invitation),
        invited_by_name=invited_by_name,
        expires_at=invitation.expires_at,
        accepted_at=invitation.accepted_at,
        revoked_at=invitation.revoked_at,
        created_at=invitation.created_at,
    )


def _org_response(org: Org, user_count: int) -> OrgResponse:
    return OrgResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        is_active=org.is_active,
        user_count=user_count,
        is_platform_org=is_platform_org(org),
        created_at=org.created_at,
    )


def _user_response(user: User, org_name: str) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        org_id=user.org_id,
        org_name=org_name,
        email=user.email,
        name=user.name,
        role=user.role.value,
        is_active=user.is_active,
        default_working_language=user.default_working_language,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


async def _org_user_count(session: AsyncSession, org_id: UUID) -> int:
    count = await session.scalar(
        select(func.count()).select_from(User).where(User.org_id == org_id),
    )
    return int(count or 0)


async def _get_org_or_404(session: AsyncSession, org_id: UUID) -> Org:
    org = await session.get(Org, org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")
    return org


async def _pending_invite_exists(session: AsyncSession, email: str) -> bool:
    result = await session.execute(
        select(UserInvitation).where(
            UserInvitation.email == email.lower(),
            UserInvitation.accepted_at.is_(None),
            UserInvitation.revoked_at.is_(None),
        ),
    )
    invitations = list(result.scalars().all())
    return any(not is_invitation_expired(invite.expires_at) for invite in invitations)


def _parse_role(role: str) -> UserRole:
    try:
        return UserRole(role)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role: {role}",
        ) from exc


def _resolve_target_org_id(current_user: User, requested_org_id: UUID | None) -> UUID:
    if is_app_admin(current_user):
        if requested_org_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="org_id is required for app admin invitations",
            )
        return requested_org_id
    return current_user.org_id


@router.get("/orgs", response_model=list[OrgResponse])
async def list_orgs(
    current_user: Annotated[User, Depends(get_app_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[OrgResponse]:
    """List all organizations (app admin only)."""
    result = await db.execute(select(Org).order_by(Org.name.asc()))
    orgs = list(result.scalars().all())
    responses: list[OrgResponse] = []
    for org in orgs:
        user_count = await _org_user_count(db, org.id)
        responses.append(_org_response(org, user_count))
    logger.info("admin_orgs_listed", count=len(responses), actor_id=str(current_user.id))
    return responses


@router.post("/orgs", response_model=OrgResponse, status_code=status.HTTP_201_CREATED)
async def create_org(
    body: CreateOrgRequest,
    current_user: Annotated[User, Depends(get_app_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrgResponse:
    """Create a new organization."""
    slug = (body.slug or slugify_org_name(body.name)).lower()
    existing = await db.execute(select(Org).where(Org.slug == slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Org slug already exists",
        )

    org = Org(name=body.name.strip(), slug=slug, is_active=True)
    db.add(org)
    await db.flush()
    logger.info("admin_org_created", org_id=str(org.id), slug=slug, actor_id=str(current_user.id))
    return _org_response(org, 0)


@router.get("/orgs/{org_id}", response_model=OrgResponse)
async def get_org(
    org_id: UUID,
    current_user: Annotated[User, Depends(get_app_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrgResponse:
    """Get organization detail."""
    org = await _get_org_or_404(db, org_id)
    user_count = await _org_user_count(db, org.id)
    return _org_response(org, user_count)


@router.patch("/orgs/{org_id}", response_model=OrgResponse)
async def update_org(
    org_id: UUID,
    body: UpdateOrgRequest,
    current_user: Annotated[User, Depends(get_app_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrgResponse:
    """Update an organization."""
    org = await _get_org_or_404(db, org_id)
    platform = is_platform_org(org)

    if body.name is not None:
        if platform:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Platform org name cannot be changed",
            )
        org.name = body.name.strip()

    if body.slug is not None:
        if platform:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Platform org slug cannot be changed",
            )
        slug = body.slug.strip().lower()
        existing = await db.execute(
            select(Org).where(Org.slug == slug, Org.id != org.id),
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Org slug already exists",
            )
        org.slug = slug

    if body.is_active is not None:
        org.is_active = body.is_active

    await db.flush()
    user_count = await _org_user_count(db, org.id)
    logger.info("admin_org_updated", org_id=str(org.id), actor_id=str(current_user.id))
    return _org_response(org, user_count)


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    current_user: Annotated[User, Depends(get_org_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    org_id: Annotated[UUID | None, Query()] = None,
) -> list[AdminUserResponse]:
    """List users visible to the current admin."""
    query = select(User, Org.name).join(Org, User.org_id == Org.id)
    if is_app_admin(current_user):
        if org_id is not None:
            query = query.where(User.org_id == org_id)
    else:
        query = query.where(User.org_id == current_user.org_id)

    query = query.order_by(User.name.asc())
    result = await db.execute(query)
    rows = list(result.all())
    logger.info("admin_users_listed", count=len(rows), actor_id=str(current_user.id))
    return [_user_response(user, org_name) for user, org_name in rows]


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_org_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminUserResponse:
    """Get a managed user."""
    result = await db.execute(
        select(User, Org.name)
        .join(Org, User.org_id == Org.id)
        .where(User.id == user_id),
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user, org_name = row
    assert_can_access_org(current_user, user.org_id)
    return _user_response(user, org_name)


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: UUID,
    body: UpdateAdminUserRequest,
    current_user: Annotated[User, Depends(get_org_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminUserResponse:
    """Update a managed user."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not can_manage_user(current_user, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot manage user")

    if body.name is not None:
        user.name = body.name.strip()

    if body.role is not None:
        role = _parse_role(body.role)
        assert_can_assign_role(current_user, role)
        user.role = role

    if body.default_working_language is not None:
        user.default_working_language = body.default_working_language

    if body.is_active is not None:
        user.is_active = body.is_active

    org = await _get_org_or_404(db, user.org_id)
    await db.flush()
    logger.info("admin_user_updated", user_id=str(user.id), actor_id=str(current_user.id))
    return _user_response(user, org.name)


@router.get("/invitations", response_model=list[InvitationResponse])
async def list_invitations(
    current_user: Annotated[User, Depends(get_org_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    org_id: Annotated[UUID | None, Query()] = None,
) -> list[InvitationResponse]:
    """List invitations visible to the current admin."""
    query = (
        select(UserInvitation, Org.name, User.name)
        .join(Org, UserInvitation.org_id == Org.id)
        .join(User, UserInvitation.invited_by == User.id)
        .order_by(UserInvitation.created_at.desc())
    )
    if is_app_admin(current_user):
        if org_id is not None:
            query = query.where(UserInvitation.org_id == org_id)
    else:
        query = query.where(UserInvitation.org_id == current_user.org_id)

    result = await db.execute(query)
    rows = list(result.all())
    return [
        _invitation_response(invitation, org_name=org_name, invited_by_name=inviter_name)
        for invitation, org_name, inviter_name in rows
    ]


@router.post(
    "/invitations",
    response_model=CreateInvitationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    body: CreateInvitationRequest,
    current_user: Annotated[User, Depends(get_org_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CreateInvitationResponse:
    """Create an invitation and return a one-time invite URL."""
    role = _parse_role(body.role)
    assert_can_assign_role(current_user, role)

    target_org_id = _resolve_target_org_id(current_user, body.org_id)
    org = await _get_org_or_404(db, target_org_id)
    assert_can_access_org(current_user, org.id)

    if not org.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot invite users to an inactive org",
        )

    email = body.email.lower().strip()
    existing_user = await get_user_by_email(db, email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    if await _pending_invite_exists(db, email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pending invitation already exists for this email",
        )

    token = generate_invite_token()
    invitation = UserInvitation(
        org_id=org.id,
        email=email,
        name=body.name.strip(),
        role=role,
        token_hash=hash_invite_token(token),
        invited_by=current_user.id,
        expires_at=invitation_expires_at(),
    )
    db.add(invitation)
    await db.flush()

    inviter = current_user
    invite_url = f"{settings.app_base_url.rstrip('/')}/en/accept-invite?token={token}"
    response = CreateInvitationResponse(
        invitation=_invitation_response(
            invitation,
            org_name=org.name,
            invited_by_name=inviter.name,
        ),
        invite_url=invite_url,
    )
    logger.info(
        "admin_invitation_created",
        invitation_id=str(invitation.id),
        org_id=str(org.id),
        email=email,
        actor_id=str(current_user.id),
    )
    return response


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def revoke_invitation(
    invitation_id: UUID,
    current_user: Annotated[User, Depends(get_org_admin_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Revoke a pending invitation."""
    invitation = await db.get(UserInvitation, invitation_id)
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    assert_can_access_org(current_user, invitation.org_id)

    if invitation.accepted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Accepted invitations cannot be revoked",
        )
    if invitation.revoked_at is not None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    invitation.revoked_at = datetime.now(UTC)
    await db.flush()
    logger.info(
        "admin_invitation_revoked",
        invitation_id=str(invitation.id),
        actor_id=str(current_user.id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
