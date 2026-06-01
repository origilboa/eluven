"""User model and UserRole enum."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, str_enum

if TYPE_CHECKING:
    from models.cluster import Cluster
    from models.org import Org
    from models.task import Task


class UserRole(str, Enum):
    """Closed set of user roles."""

    APP_ADMIN = "app_admin"
    ORG_ADMIN = "org_admin"
    USER = "user"


class User(Base):
    """User account within an organization."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("orgs.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(str_enum(UserRole), default=UserRole.USER)
    default_working_language: Mapped[str] = mapped_column(String(10), default="en")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)

    org: Mapped[Org] = relationship(back_populates="users")
    tasks: Mapped[list[Task]] = relationship(back_populates="owner")
    clusters: Mapped[list[Cluster]] = relationship(back_populates="owner")
