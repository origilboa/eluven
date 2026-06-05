"""Load activity studio agent charters from disk."""

from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path

from core.logging import get_logger

logger = get_logger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_INSTRUCTIONS_DIR = _BACKEND_DIR.parent / "docs" / "instructions"
_VERSION_PATTERN = re.compile(r"^\*\*Version:\*\*\s*(\S+)", re.MULTILINE)


def charter_version_from_text(text: str) -> str:
    """Parse version header from charter markdown."""
    match = _VERSION_PATTERN.search(text)
    if match:
        return match.group(1)
    return "unknown"


@lru_cache(maxsize=4)
def load_prompt_authoring_charter() -> str:
    """Load activity prompt authoring agent charter."""
    path = _INSTRUCTIONS_DIR / "activity-prompt-authoring-agent-charter.md"
    text = path.read_text(encoding="utf-8")
    logger.info(
        "prompt_authoring_charter_loaded",
        path=str(path),
        version=charter_version_from_text(text),
        content_hash=hashlib.sha256(text.encode()).hexdigest()[:16],
    )
    return text


@lru_cache(maxsize=4)
def load_orchestrator_charter() -> str:
    """Load activity type orchestrator charter."""
    path = _INSTRUCTIONS_DIR / "activity-type-orchestrator-charter.md"
    text = path.read_text(encoding="utf-8")
    logger.info(
        "activity_orchestrator_charter_loaded",
        path=str(path),
        version=charter_version_from_text(text),
        content_hash=hashlib.sha256(text.encode()).hexdigest()[:16],
    )
    return text


def prompt_charter_version() -> str:
    return charter_version_from_text(load_prompt_authoring_charter())


def orchestrator_charter_version() -> str:
    return charter_version_from_text(load_orchestrator_charter())
