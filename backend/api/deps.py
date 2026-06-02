"""Shared FastAPI dependencies for API routes."""

from typing import Annotated

from fastapi import Depends

from api.admin_access import require_app_admin, require_org_admin_or_above
from core.database import get_db
from core.security import get_current_active_user, get_current_user
from models.user import User

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_active_user",
    "get_org_admin_user",
    "get_app_admin_user",
]


async def get_org_admin_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Require org_admin or app_admin."""
    return require_org_admin_or_above(current_user)


async def get_app_admin_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Require app_admin."""
    return require_app_admin(current_user)
