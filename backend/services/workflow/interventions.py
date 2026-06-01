"""Detect workflow intervention triggers in AI responses."""

# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from core.config import settings
from core.logging import get_logger
from models.workflow import InterventionTriggerType
from schemas.task_memory import TaskMemoryEntryPayload

logger = get_logger(__name__)

_INTERVENTION_BLOCK_PATTERN = re.compile(
    r"```intervention\s*\n(\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)

_TRIGGER_TYPE_VALUES = {trigger.value for trigger in InterventionTriggerType}


@dataclass(frozen=True)
class DetectedIntervention:
    """Parsed intervention trigger from an automated thread response."""

    trigger_type: InterventionTriggerType
    question: str


def detect_intervention(
    response_text: str,
    *,
    memory_payloads: list[TaskMemoryEntryPayload] | None = None,
) -> DetectedIntervention | None:
    """Return the first intervention trigger found in the AI response."""
    explicit = _parse_intervention_blocks(response_text)
    if explicit is not None:
        return explicit

    if memory_payloads:
        low_confidence = _detect_low_confidence(memory_payloads)
        if low_confidence is not None:
            return low_confidence

    return None


def _parse_intervention_blocks(response_text: str) -> DetectedIntervention | None:
    for raw_json in _INTERVENTION_BLOCK_PATTERN.findall(response_text):
        detected = _parse_intervention_json(raw_json)
        if detected is not None:
            return detected

    for line in response_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("{"):
            continue
        detected = _parse_intervention_json(stripped)
        if detected is not None:
            return detected

    return None


def _parse_intervention_json(raw_json: str) -> DetectedIntervention | None:
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None

    trigger_raw = data.get("trigger_type") or data.get("type")
    if trigger_raw not in _TRIGGER_TYPE_VALUES:
        return None

    question = data.get("question") or data.get("message")
    if not question or not isinstance(question, str):
        question = "The workflow requires your input before continuing."

    return DetectedIntervention(
        trigger_type=InterventionTriggerType(str(trigger_raw)),
        question=question.strip(),
    )


def _detect_low_confidence(
    memory_payloads: list[TaskMemoryEntryPayload],
) -> DetectedIntervention | None:
    threshold = settings.workflow_confidence_threshold
    low_entries = [
        payload
        for payload in memory_payloads
        if payload.confidence is not None and payload.confidence < threshold
    ]
    if not low_entries:
        return None

    summary = "; ".join(payload.content[:120] for payload in low_entries[:3])
    logger.info(
        "workflow_intervention_low_confidence_detected",
        entry_count=len(low_entries),
        threshold=threshold,
    )
    return DetectedIntervention(
        trigger_type=InterventionTriggerType.CONFIDENCE_BELOW_THRESHOLD,
        question=(
            "One or more findings were recorded with low confidence. "
            f"Please clarify before the workflow continues. Summary: {summary}"
        ),
    )
