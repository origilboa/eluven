"""Authentication endpoints (data model Section 10.1)."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_active_user, get_db
from core.config import settings
from core.logging import get_logger
from core.security import (
    create_token,
    decode_token,
    get_user_by_email,
    get_user_by_id,
    verify_password,
)
from models.user import User
from schemas.auth import (
    AuthResponse,
    LoginRequest,
    RefreshRequest,
    RefreshResponse,
    UserResponse,
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
