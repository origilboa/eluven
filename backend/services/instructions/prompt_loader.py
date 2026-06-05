"""Load instruction authoring charter and per-level briefs from disk."""

from __future__ import annotations

import hashlib
import re
from functools import lru_cache
from pathlib import Path

from core.config import settings
from core.logging import get_logger
from models.instruction import InstructionLevel

logger = get_logger(__name__)

_BACKEND_DIR = Path(__file__).resolve().parents[2]
_DEFAULT_INSTRUCTIONS_DIR = _BACKEND_DIR.parent / "docs" / "instructions"
_VERSION_PATTERN = re.compile(r"^\*\*Version:\*\*\s*(\S+)", re.MULTILINE)


@lru_cache(maxsize=1)
def _charter_path() -> Path:
    configured = settings.instruction_authoring_charter_path.strip()
    if configured:
        return Path(configured)
    return _DEFAULT_INSTRUCTIONS_DIR / "authoring-agent-charter.md"


@lru_cache(maxsize=1)
def _briefs_dir() -> Path:
    configured = settings.instruction_authoring_briefs_dir.strip()
    if configured:
        return Path(configured)
    return _DEFAULT_INSTRUCTIONS_DIR / "authoring-level-briefs"


def charter_version_from_text(text: str) -> str:
    """Parse version header from charter markdown."""
    match = _VERSION_PATTERN.search(text)
    if match:
        return match.group(1)
    return "unknown"


@lru_cache(maxsize=4)
def load_charter_text() -> str:
    """Load agent charter markdown."""
    path = _charter_path()
    text = path.read_text(encoding="utf-8")
    logger.info(
        "instruction_authoring_charter_loaded",
        path=str(path),
        version=charter_version_from_text(text),
        content_hash=hashlib.sha256(text.encode()).hexdigest()[:16],
    )
    return text


def load_level_brief(level: InstructionLevel) -> str:
    """Load level-specific authoring brief."""
    path = _briefs_dir() / f"{level.value}.md"
    if not path.is_file():
        logger.warning(
            "instruction_authoring_brief_missing",
            level=level.value,
            path=str(path),
        )
        return ""
    return path.read_text(encoding="utf-8")


def charter_version() -> str:
    """Return parsed charter version for logging."""
    return charter_version_from_text(load_charter_text())


@lru_cache(maxsize=1)
def load_precedence_text() -> str:
    """Load runtime InstructionLayer precedence directive."""
    path = _DEFAULT_INSTRUCTIONS_DIR / "instruction-layer-precedence.md"
    if not path.is_file():
        logger.warning("instruction_precedence_missing", path=str(path))
        return ""
    return path.read_text(encoding="utf-8")
