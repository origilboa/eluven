"""Password hashing, JWT utilities, and authentication dependencies."""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal
from uuid import UUID

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.logging import get_logger
from models.user import User

logger = get_logger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if the plaintext password matches the bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def _token_expiry(token_type: TokenType) -> datetime:
    if token_type == "access":
        return datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    return datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)


def create_token(*, user_id: UUID, org_id: UUID, token_type: TokenType) -> str:
    """Create a signed JWT for the given user."""
    expire = _token_expiry(token_type)
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "org_id": str(org_id),
        "type": token_type,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
    }
    token = jwt.encode(  # pyright: ignore[reportUnknownMemberType]
        payload,
        settings.nextauth_secret,
        algorithm=settings.jwt_algorithm,
    )
    logger.info(
        "token_created",
        user_id=str(user_id),
        token_type=token_type,
        expires_at=expire.isoformat(),
    )
    return token


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT; raise HTTPException on failure."""
    try:
        payload = jwt.decode(  # pyright: ignore[reportUnknownMemberType]
            token,
            settings.nextauth_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        logger.info("token_expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.InvalidTokenError as exc:
        logger.info("token_invalid")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User | None:
    """Load a user by primary key."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Load a user by email address."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """FastAPI dependency: require a valid access token and return the User."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(str(sub))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = await get_user_by_id(db, user_id)
    if user is None:
        logger.info("auth_user_not_found", user_id=str(user_id))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """FastAPI dependency: require an active user account."""
    if not current_user.is_active:
        logger.info("auth_inactive_user", user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user
