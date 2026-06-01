"""Shared FastAPI dependencies for API routes."""

from core.database import get_db
from core.security import get_current_active_user, get_current_user

__all__ = ["get_db", "get_current_user", "get_current_active_user"]
