"""Admin API schemas (Section 10.9)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class OrgResponse(BaseModel):
    """Organization summary for admin listings."""

    id: UUID
    name: str
    slug: str
    is_active: bool
    user_count: int
    is_platform_org: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateOrgRequest(BaseModel):
    """Create a new organization."""

    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=100)


class UpdateOrgRequest(BaseModel):
    """Update organization fields."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class AdminUserResponse(BaseModel):
    """User record for admin management."""

    id: UUID
    org_id: UUID
    org_name: str
    email: str
    name: str
    role: str
    is_active: bool
    default_working_language: str
    last_login_at: datetime | None
    created_at: datetime


class UpdateAdminUserRequest(BaseModel):
    """Update a managed user."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = None
    default_working_language: str | None = Field(default=None, min_length=2, max_length=10)
    is_active: bool | None = None


class InvitationResponse(BaseModel):
    """Invitation summary (no token)."""

    id: UUID
    org_id: UUID
    org_name: str
    email: str
    name: str
    role: str
    status: str
    invited_by_name: str
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class CreateInvitationRequest(BaseModel):
    """Invite a user to an organization."""

    email: EmailStr
    name: str = Field(min_length=1, max_length=255)
    role: str = Field(default="user")
    org_id: UUID | None = None


class CreateInvitationResponse(BaseModel):
    """Invitation created with one-time invite URL."""

    invitation: InvitationResponse
    invite_url: str


class InvitationPreviewResponse(BaseModel):
    """Public preview for accept-invite page."""

    email: str
    name: str
    org_name: str
    role: str
    expires_at: datetime
    is_valid: bool
