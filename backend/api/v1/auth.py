"""Authentication endpoints (data model Section 10.1)."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user, get_db
from core.config import settings
from core.logging import get_logger
from core.security import (
    create_token,
    decode_token,
    get_user_by_email,
    get_user_by_id,
    hash_password,
    verify_password,
)
from models.invitation import UserInvitation
from models.org import Org
from models.user import User
from schemas.admin import InvitationPreviewResponse
from schemas.auth import (
    AcceptInviteRequest,
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RefreshResponse,
    UserResponse,
)
from services.invitations import (
    hash_invite_token,
    is_invitation_expired,
    normalize_invite_token,
)

logger = get_logger(__name__)

router = APIRouter()

REFRESH_COOKIE = "refresh_token"


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        org_id=user.org_id,
        default_working_language=user.default_working_language,
    )


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        max_age=settings.jwt_refresh_token_expire_days * 86_400,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE)


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Authenticate with email and password; return access token and user profile."""
    logger.info("auth_login_attempt", email=body.email)

    user = await get_user_by_email(db, body.email)
    if user is None or not verify_password(body.password, user.hashed_password):
        logger.info("auth_login_failed", email=body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not user.is_active:
        logger.info("auth_login_inactive", user_id=str(user.id))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    user.last_login_at = datetime.utcnow()
    await db.flush()

    access_token = create_token(user_id=user.id, org_id=user.org_id, token_type="access")
    refresh_token = create_token(user_id=user.id, org_id=user.org_id, token_type="refresh")
    _set_refresh_cookie(response, refresh_token)

    logger.info("auth_login_success", user_id=str(user.id), org_id=str(user.org_id))

    return AuthResponse(
        access_token=access_token,
        user=_user_response(user),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    """Invalidate client session (clear refresh cookie)."""
    _clear_refresh_cookie(response)
    logger.info("auth_logout", user_id=str(current_user.id))


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    body: RefreshRequest | None = None,
) -> RefreshResponse:
    """Issue a new access token using a valid refresh token."""
    token = body.refresh_token if body is not None else request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    try:
        user_id = UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        ) from exc

    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    access_token = create_token(user_id=user.id, org_id=user.org_id, token_type="access")
    new_refresh_token = create_token(user_id=user.id, org_id=user.org_id, token_type="refresh")
    _set_refresh_cookie(response, new_refresh_token)

    logger.info("auth_token_refreshed", user_id=str(user.id))

    return RefreshResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@router.get("/me", response_model=UserResponse)
async def me(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    """Return the authenticated user's profile."""
    logger.info("auth_me", user_id=str(current_user.id))
    return _user_response(current_user)


async def _get_valid_invitation(
    db: AsyncSession,
    token: str,
) -> tuple[UserInvitation, Org]:
    try:
        normalized = normalize_invite_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invitation token",
        ) from exc

    token_hash = hash_invite_token(normalized)
    result = await db.execute(
        select(UserInvitation).where(UserInvitation.token_hash == token_hash),
    )
    invitation = result.scalar_one_or_none()
    if invitation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    org = await db.get(Org, invitation.org_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation org not found",
        )

    return invitation, org


def _invitation_is_valid(invitation: UserInvitation, org: Org) -> bool:
    if invitation.revoked_at is not None:
        return False
    if invitation.accepted_at is not None:
        return False
    if is_invitation_expired(invitation.expires_at):
        return False
    return org.is_active


@router.get("/invitations/preview", response_model=InvitationPreviewResponse)
async def preview_invitation(
    db: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str, Query(min_length=32)],
) -> InvitationPreviewResponse:
    """Return public invitation preview for the accept-invite page."""
    invitation, org = await _get_valid_invitation(db, token)
    valid = _invitation_is_valid(invitation, org)
    logger.info(
        "auth_invitation_preview",
        invitation_id=str(invitation.id),
        is_valid=valid,
    )
    return InvitationPreviewResponse(
        email=invitation.email,
        name=invitation.name,
        org_name=org.name,
        role=invitation.role.value,
        expires_at=invitation.expires_at,
        is_valid=valid,
    )


@router.post("/accept-invite", response_model=AuthResponse)
async def accept_invite(
    body: AcceptInviteRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuthResponse:
    """Accept an invitation, create the user account, and sign in."""
    invitation, org = await _get_valid_invitation(db, body.token)
    if not _invitation_is_valid(invitation, org):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation is no longer valid",
        )

    existing_user = await get_user_by_email(db, invitation.email)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        org_id=invitation.org_id,
        email=invitation.email,
        name=invitation.name,
        role=invitation.role,
        hashed_password=hash_password(body.password),
        is_active=True,
        default_working_language="en",
    )
    db.add(user)
    invitation.accepted_at = datetime.now(UTC)
    await db.flush()

    access_token = create_token(user_id=user.id, org_id=user.org_id, token_type="access")
    refresh_token = create_token(user_id=user.id, org_id=user.org_id, token_type="refresh")
    _set_refresh_cookie(response, refresh_token)

    logger.info(
        "auth_invite_accepted",
        user_id=str(user.id),
        invitation_id=str(invitation.id),
        org_id=str(user.org_id),
    )

    return AuthResponse(
        access_token=access_token,
        user=_user_response(user),
    )
