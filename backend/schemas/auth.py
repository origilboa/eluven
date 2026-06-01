"""Auth API schemas (data model Section 10.1)."""

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Credentials for email/password login."""

    email: EmailStr
    password: str = Field(min_length=1)


class UserResponse(BaseModel):
    """Public user profile returned to clients."""

    id: UUID
    email: str
    name: str
    role: str
    org_id: UUID
    default_working_language: str

    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Access token and user profile after successful authentication."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    """Refresh token for issuing a new access token."""

    refresh_token: str = Field(min_length=1)


class RefreshResponse(BaseModel):
    """New access token after refresh."""

    access_token: str
    token_type: str = "bearer"
    refresh_token: str
