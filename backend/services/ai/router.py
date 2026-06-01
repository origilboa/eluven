"""Model routing via ActivityLibrary entries."""

from __future__ import annotations

from dataclasses import dataclass

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logging import get_logger
from models.activity import ActivityLibraryEntry

logger = get_logger(__name__)

_SCOPE_PRIORITY = {"org": 0, "user": 1, "platform": 2}


@dataclass(frozen=True)
class RoutingRule:
    """Bedrock model routing for a thread type."""

    default_model_id: str
    fallback_model_id: str | None


class AIRouter:
    """Resolve Bedrock model IDs from ActivityLibrary configuration."""

    def __init__(self) -> None:
        self._cache: dict[str, RoutingRule] = {}
        self._loaded = False

    async def ensure_loaded(self, session: AsyncSession, org_id: UUID | None = None) -> None:
        """Load routing rules from the database on first use."""
        if self._loaded:
            return

        query = select(ActivityLibraryEntry).where(ActivityLibraryEntry.is_active.is_(True))
        if org_id is not None:
            query = query.where(
                or_(
                    ActivityLibraryEntry.scope == "platform",
                    ActivityLibraryEntry.org_id == org_id,
                ),
            )
        result = await session.execute(query)
        entries = result.scalars().all()

        best_by_type: dict[str, tuple[int, RoutingRule]] = {}
        for entry in entries:
            rank = _scope_rank(entry.scope)
            rule = RoutingRule(
                default_model_id=entry.default_model_id,
                fallback_model_id=entry.fallback_model_id,
            )
            current = best_by_type.get(entry.thread_type)
            if current is None or rank < current[0]:
                best_by_type[entry.thread_type] = (rank, rule)
        self._cache = {key: value[1] for key, value in best_by_type.items()}

        self._loaded = True
        logger.info("ai_router_cache_loaded", thread_type_count=len(self._cache))

    def get_model(self, thread_type: str, budget_warning: bool = False) -> str:
        """Return the Bedrock model ID for a thread type."""
        rule = self._cache.get(thread_type)
        if rule is None:
            logger.info(
                "ai_router_default_model",
                thread_type=thread_type,
                model_id=settings.default_bedrock_model_id,
            )
            return settings.default_bedrock_model_id

        if budget_warning and rule.fallback_model_id:
            logger.info(
                "ai_router_fallback_model",
                thread_type=thread_type,
                model_id=rule.fallback_model_id,
            )
            return rule.fallback_model_id

        logger.info(
            "ai_router_default_model",
            thread_type=thread_type,
            model_id=rule.default_model_id,
        )
        return rule.default_model_id


def _scope_rank(scope: str) -> int:
    return _SCOPE_PRIORITY.get(scope, 99)
