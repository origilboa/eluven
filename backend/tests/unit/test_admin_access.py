"""Unit tests for admin access helpers."""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from api.admin_access import (
    assert_can_assign_role,
    can_assign_role,
    can_manage_user,
    is_app_admin,
    is_org_admin_or_above,
    require_org_admin_or_above,
)
from core.platform import PLATFORM_ORG_ID
from models.org import Org
from models.user import User, UserRole


def _user(role: UserRole, org_id=None) -> User:
    return User(
        id=uuid4(),
        org_id=org_id or uuid4(),
        email=f"{role.value}@example.com",
        name="Test User",
        role=role,
        hashed_password="hash",
    )


def test_is_app_admin() -> None:
    assert is_app_admin(_user(UserRole.APP_ADMIN)) is True
    assert is_app_admin(_user(UserRole.ORG_ADMIN)) is False


def test_is_org_admin_or_above() -> None:
    assert is_org_admin_or_above(_user(UserRole.USER)) is False
    assert is_org_admin_or_above(_user(UserRole.ORG_ADMIN)) is True


def test_require_org_admin_or_above_rejects_user() -> None:
    with pytest.raises(HTTPException) as exc_info:
        require_org_admin_or_above(_user(UserRole.USER))
    assert exc_info.value.status_code == 403


def test_can_assign_role_matrix() -> None:
    app_admin = _user(UserRole.APP_ADMIN)
    org_admin = _user(UserRole.ORG_ADMIN)

    assert can_assign_role(app_admin, UserRole.APP_ADMIN) is True
    assert can_assign_role(org_admin, UserRole.APP_ADMIN) is False
    assert can_assign_role(org_admin, UserRole.ORG_ADMIN) is True
    assert can_assign_role(org_admin, UserRole.USER) is True


def test_assert_can_assign_role_raises() -> None:
    org_admin = _user(UserRole.ORG_ADMIN)
    with pytest.raises(HTTPException):
        assert_can_assign_role(org_admin, UserRole.APP_ADMIN)


def test_can_manage_user_rules() -> None:
    org_id = uuid4()
    actor = _user(UserRole.ORG_ADMIN, org_id)
    target = _user(UserRole.USER, org_id)
    actor.id = uuid4()
    target.id = uuid4()

    assert can_manage_user(actor, target) is True
    assert can_manage_user(actor, actor) is False

    app_target = _user(UserRole.APP_ADMIN, org_id)
    assert can_manage_user(actor, app_target) is False


def test_platform_org_detection() -> None:
    from api.admin_access import is_platform_org

    platform = Org(id=PLATFORM_ORG_ID, name="Eluven", slug="eluven")
    other = Org(id=uuid4(), name="Dev Org", slug="dev-org")
    assert is_platform_org(platform) is True
    assert is_platform_org(other) is False
