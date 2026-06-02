"""Tests for admin ActivityLibrary API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from api.v1 import admin_activity_library as admin_al
from models.activity import ActivityLibraryEntry
from models.user import User, UserRole
from schemas.admin_activity import CreateActivityLibraryEntryRequest


@pytest.mark.asyncio
async def test_create_rejects_unknown_module_type() -> None:
    admin = User(
        id=uuid4(),
        org_id=uuid4(),
        email="admin@eluven.ai",
        name="Admin",
        role=UserRole.APP_ADMIN,
        hashed_password="x",
    )
    db = AsyncMock()

    body = CreateActivityLibraryEntryRequest(
        thread_type="custom_type",
        module_type="unknown_module",
        display_name="Custom",
    )

    with pytest.raises(HTTPException) as exc_info:
        await admin_al.create_admin_activity_library_entry(body, admin, db)

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_get_platform_entry_not_found() -> None:
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)

    with pytest.raises(HTTPException) as exc_info:
        await admin_al._get_platform_entry(db, uuid4())

    assert exc_info.value.status_code == 404


def test_entry_response_maps_fields() -> None:
    entry = MagicMock(spec=ActivityLibraryEntry)
    entry.id = uuid4()
    entry.thread_type = "initial_read"
    entry.module_type = "external_paper_review"
    entry.display_name = "Initial Read"
    entry.description = None
    entry.scope = "platform"
    entry.is_active = True
    entry.default_model_id = "model"
    entry.fallback_model_id = None
    entry.token_budget = 20000
    entry.token_budget_warning_threshold = 0.8
    entry.supports_automation = True
    entry.default_instruction_content = "Review the paper."
    entry.created_at = entry.updated_at = MagicMock()

    response = admin_al._entry_response(entry, opening_question_count=3)
    assert response.thread_type == "initial_read"
    assert response.opening_question_count == 3
    assert response.default_instruction_content == "Review the paper."
