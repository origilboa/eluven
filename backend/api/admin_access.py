"""Admin access helpers and role guards."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from core.platform import PLATFORM_ORG_ID
from models.org import Org
from models.user import User, UserRole


def is_app_admin(user: User) -> bool:
    return user.role == UserRole.APP_ADMIN


def is_org_admin_or_above(user: User) -> bool:
    return user.role in (UserRole.APP_ADMIN, UserRole.ORG_ADMIN)


def require_org_admin_or_above(user: User) -> User:
    if not is_org_admin_or_above(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def require_app_admin(user: User) -> User:
    if not is_app_admin(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="App admin access required",
        )
    return user


def can_access_org(user: User, org_id: UUID) -> bool:
    if is_app_admin(user):
        return True
    return user.org_id == org_id


def assert_can_access_org(user: User, org_id: UUID) -> None:
    if not can_access_org(user, org_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found")


def can_assign_role(actor: User, role: UserRole) -> bool:
    if role == UserRole.APP_ADMIN:
        return is_app_admin(actor)
    return is_org_admin_or_above(actor)


def assert_can_assign_role(actor: User, role: UserRole) -> None:
    if not can_assign_role(actor, role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot assign role: {role.value}",
        )


def can_manage_user(actor: User, target: User) -> bool:
    if actor.id == target.id:
        return False
    if not can_access_org(actor, target.org_id):
        return False
    if target.role == UserRole.APP_ADMIN and not is_app_admin(actor):
        return False
    return is_org_admin_or_above(actor)


def is_platform_org(org: Org) -> bool:
    return org.id == PLATFORM_ORG_ID
