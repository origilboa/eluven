"""Merge entity structured/freeform tags for AI context assembly."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.cluster import Cluster
from models.task import Task


def _format_tag_lines(label: str, tags: dict[str, Any] | None) -> list[str]:
    if not tags:
        return []
    lines = [f"{label}:"]
    for key, value in sorted(tags.items()):
        if isinstance(value, (list, dict)):
            rendered = json.dumps(value, ensure_ascii=False)
        else:
            rendered = str(value)
        lines.append(f"  {key}: {rendered}")
    return lines


def format_merged_tags_block(
    *,
    assignment_tags: dict[str, Any] | None = None,
    task_tags: dict[str, Any] | None = None,
    freeform_tags: list[str] | None = None,
) -> str:
    """Render structured and freeform tags for the context assembler."""
    lines: list[str] = []
    lines.extend(_format_tag_lines("Assignment tags", assignment_tags))
    lines.extend(_format_tag_lines("Task tags", task_tags))
    if freeform_tags:
        lines.append("Freeform tags: " + ", ".join(sorted(set(freeform_tags))))
    if not lines:
        return ""
    return "## Tags\n" + "\n".join(lines)


async def load_merged_tags_for_task(
    session: AsyncSession,
    task: Task,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    """Return assignment tags, task tags, and merged freeform tags."""
    assignment_tags: dict[str, Any] = {}
    assignment_freeform: list[str] = []
    if task.cluster_id is not None:
        cluster = await session.get(Cluster, task.cluster_id)
        if cluster is not None:
            assignment_tags = dict(cluster.structured_tags or {})
            assignment_freeform = list(cluster.freeform_tags or [])

    task_tags = dict(task.structured_tags or {})
    task_freeform = list(task.freeform_tags or [])
    merged_freeform = sorted(set(assignment_freeform + task_freeform))
    return assignment_tags, task_tags, merged_freeform
