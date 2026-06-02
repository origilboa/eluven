"""Unit tests for invitation token utilities."""

import pytest

from services.invitations import (
    generate_invite_token,
    hash_invite_token,
    is_invitation_expired,
    normalize_invite_token,
    slugify_org_name,
)
from datetime import datetime, timedelta


def test_generate_and_hash_token() -> None:
    token = generate_invite_token()
    assert len(token) >= 32
    assert hash_invite_token(token) == hash_invite_token(token)


def test_normalize_invite_token_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        normalize_invite_token("bad token!")


def test_is_invitation_expired() -> None:
    past = datetime.utcnow() - timedelta(days=1)
    future = datetime.utcnow() + timedelta(days=1)
    assert is_invitation_expired(past) is True
    assert is_invitation_expired(future) is False


def test_slugify_org_name() -> None:
    assert slugify_org_name("Dev Org") == "dev-org"
    assert slugify_org_name("  Hello World!  ") == "hello-world"
