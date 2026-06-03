"""Shared KB query helpers for API routes."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.kb import KBDocument


async def collection_document_count(session: AsyncSession, collection_id: UUID) -> int:
    """Count non-deleted documents in a KBCollection."""
    count = await session.scalar(
        select(func.count())
        .select_from(KBDocument)
        .where(
            KBDocument.collection_id == collection_id,
            KBDocument.is_deleted.is_(False),
        ),
    )
    return int(count or 0)
