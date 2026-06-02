"""Invitation token utilities and validation."""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta

from core.config import settings

_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]{32,128}$")


def generate_invite_token() -> str:
    """Return a URL-safe invitation token."""
    return secrets.token_urlsafe(32)


def hash_invite_token(token: str) -> str:
    """Hash an invitation token for storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def invitation_expires_at() -> datetime:
    """Compute default invitation expiry timestamp (naive UTC for DB compatibility)."""
    return datetime.utcnow() + timedelta(days=settings.invitation_expire_days)


def is_invitation_expired(expires_at: datetime) -> bool:
    """Return True if the invitation expiry is in the past."""
    now = datetime.utcnow()
    expiry = expires_at.replace(tzinfo=None) if expires_at.tzinfo is not None else expires_at
    return expiry <= now


def normalize_invite_token(token: str) -> str:
    """Validate token format before lookup."""
    cleaned = token.strip()
    if not _TOKEN_PATTERN.fullmatch(cleaned):
        msg = "Invalid invitation token"
        raise ValueError(msg)
    return cleaned


def slugify_org_name(name: str) -> str:
    """Derive a URL-safe org slug from a display name."""
    slug = name.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:100] or "org"
