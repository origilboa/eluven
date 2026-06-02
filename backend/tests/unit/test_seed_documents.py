"""Unit tests for demo seed document helpers."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from models.kb import KBDocumentStatus, TaskDocument
from models.org import Org
from models.task import Task
from models.user import User, UserRole
from seed import documents as seed_documents


@pytest.fixture
def org() -> Org:
    return Org(id=uuid4(), name="Dev Org", slug="dev-org")


@pytest.fixture
def user(org: Org) -> User:
    return User(
        id=uuid4(),
        org_id=org.id,
        email="dev@eluven.ai",
        name="Dev",
        role=UserRole.APP_ADMIN,
        hashed_password="x",
    )


@pytest.fixture
def task(org: Org, user: User) -> Task:
    return Task(
        id=uuid4(),
        org_id=org.id,
        owner_id=user.id,
        title="Demo task",
        module_type="external_paper_review",
    )


def test_seed_skip_aws_env() -> None:
    with patch.dict(os.environ, {"SEED_SKIP_AWS": "1"}):
        assert seed_documents.seed_skip_aws() is True
    with patch.dict(os.environ, {"SEED_SKIP_AWS": ""}, clear=False):
        assert seed_documents.seed_skip_aws() is False


@pytest.mark.asyncio
async def test_seed_task_document_skips_when_exists(
    org: Org,
    user: User,
    task: Task,
) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=uuid4())),
    )

    created = await seed_documents.seed_task_document(
        session,
        org=org,
        task=task,
        owner=user,
        filename="demo-manuscript.pdf",
        fixture_name="sample.pdf",
    )

    assert created is False


@pytest.mark.asyncio
async def test_seed_task_document_skips_upload_when_seed_skip_aws(
    org: Org,
    user: User,
    task: Task,
) -> None:
    session = AsyncMock()
    session.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
    )
    session.add = MagicMock()
    session.flush = AsyncMock()

    with (
        patch.dict(os.environ, {"SEED_SKIP_AWS": "true"}),
        patch.object(
            seed_documents,
            "read_fixture_bytes",
            return_value=(b"pdf", "pdf", "application/pdf"),
        ),
        patch.object(seed_documents, "StorageService") as storage_cls,
    ):
        created = await seed_documents.seed_task_document(
            session,
            org=org,
            task=task,
            owner=user,
            filename="demo-manuscript.pdf",
            fixture_name="sample.pdf",
        )

    assert created is True
    storage_cls.assert_not_called()
    added = session.add.call_args[0][0]
    assert isinstance(added, TaskDocument)
    assert added.status == KBDocumentStatus.PENDING
