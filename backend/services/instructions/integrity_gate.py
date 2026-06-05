"""Instruction draft integrity approval tokens and content hashing."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import time
from typing import Literal

from fastapi import HTTPException, status

from core.config import settings
from models.instruction import InstructionSet
from schemas.instruction_assistant import AuthoringTarget, InstructionAssistantScope

_TOKEN_TTL_SECONDS = 30 * 60
_BEDROCK_MODEL_PATTERN = re.compile(
    r"(?:us\.)?anthropic\.claude|us\.anthropic\.claude",
    re.IGNORECASE,
)
_TOKEN_BUDGET_PATTERN = re.compile(
    r"token\s*budget|max\s*tokens?\s*[:=]\s*\d+",
    re.IGNORECASE,
)


def normalize_draft_content(content: str) -> str:
    """Normalize draft text for stable hashing."""
    return content.replace("\r\n", "\n").strip()


def compute_content_hash(content: str) -> str:
    """SHA-256 hex digest of normalized instruction content."""
    normalized = normalize_draft_content(content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def scope_key_from_assistant_scope(scope: InstructionAssistantScope) -> str:
    """Stable scope identifier for token binding."""
    parts = [
        scope.authoring_target.value,
        scope.level,
        scope.thread_type or "",
        scope.module_type or "",
        scope.cluster_id or "",
        scope.task_id or "",
        scope.thread_id or "",
        scope.activity_entry_id or "",
    ]
    return "|".join(parts)


def scope_key_from_instruction_set(instruction_set: InstructionSet) -> str:
    """Build scope key from persisted InstructionSet (matches assistant scope)."""
    scope = InstructionAssistantScope(
        authoring_target=AuthoringTarget.INSTRUCTION_SET,
        level=instruction_set.level.value,  # type: ignore[arg-type]
        thread_type=instruction_set.thread_type,
        cluster_id=str(instruction_set.cluster_id) if instruction_set.cluster_id else None,
        task_id=str(instruction_set.task_id) if instruction_set.task_id else None,
        thread_id=str(instruction_set.thread_id) if instruction_set.thread_id else None,
    )
    return scope_key_from_assistant_scope(scope)


def scope_key_for_activity_entry(
    *,
    level: Literal["platform", "org"],
    thread_type: str,
    module_type: str,
    entry_id: str | None = None,
) -> str:
    """Scope key for ActivityLibrary default_instruction_content."""
    parts = [
        "activity_library_default",
        level,
        thread_type,
        module_type,
        "",
        "",
        "",
        entry_id or "",
    ]
    return "|".join(parts)


def issue_approval_token(
    *,
    user_id: str,
    scope_key: str,
    content_hash: str,
) -> tuple[str, int]:
    """Issue HMAC approval token bound to user, scope, and content hash."""
    expires_at = int(time.time()) + _TOKEN_TTL_SECONDS
    payload = json.dumps(
        {
            "user_id": user_id,
            "scope_key": scope_key,
            "content_hash": content_hash,
            "exp": expires_at,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    signature = hmac.new(
        settings.nextauth_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    token = f"{signature}.{payload}"
    return token, expires_at


def verify_approval_token(
    *,
    user_id: str,
    scope_key: str,
    content_hash: str,
    token: str,
) -> bool:
    """Verify approval token matches user, scope, content, and expiry."""
    try:
        signature, payload = token.split(".", 1)
        data = json.loads(payload)
    except (ValueError, json.JSONDecodeError):
        return False

    expected_sig = hmac.new(
        settings.nextauth_secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_sig):
        return False

    if data.get("user_id") != user_id:
        return False
    if data.get("scope_key") != scope_key:
        return False
    if data.get("content_hash") != content_hash:
        return False
    if int(data.get("exp", 0)) < int(time.time()):
        return False
    return True


def require_activity_default_integrity_approval(
    *,
    user_id: str,
    level: Literal["platform", "org"],
    thread_type: str,
    module_type: str,
    entry_id: str | None,
    content: str | None,
    token: str | None,
) -> None:
    """Raise when activity default instructions lack valid integrity approval."""
    if not content or not normalize_draft_content(content):
        return
    require_instruction_integrity_approval(
        user_id=user_id,
        scope_key=scope_key_for_activity_entry(
            level=level,
            thread_type=thread_type,
            module_type=module_type,
            entry_id=entry_id,
        ),
        content=content,
        token=token,
    )


def require_instruction_integrity_approval(
    *,
    user_id: str,
    scope_key: str,
    content: str,
    token: str | None,
) -> None:
    """Raise HTTP 400 when integrity approval is missing or invalid."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instruction integrity approval required. Run integrity review before saving.",
        )
    content_hash = compute_content_hash(content)
    if not verify_approval_token(
        user_id=user_id,
        scope_key=scope_key,
        content_hash=content_hash,
        token=token,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instruction integrity approval is stale or invalid. Re-run integrity review.",
        )


def deterministic_integrity_issues(content: str) -> list[dict[str, str]]:
    """Fast rule-based checks before LLM integrity review."""
    issues: list[dict[str, str]] = []
    if _BEDROCK_MODEL_PATTERN.search(content):
        issues.append(
            {
                "code": "wrong_bucket",
                "severity": "blocking",
                "title": "Model routing in instructions",
                "message": (
                    "Model IDs belong in Activity Settings, not instruction text. "
                    "Thread AI reads model routing from ActivityLibrary configuration."
                ),
                "recommendation": (
                    "Remove model IDs from this draft and set default_model_id "
                    "in the Activity Settings tab instead."
                ),
                "fix_strategy": "relocate_to_settings",
                "suggested_target": "Settings",
            },
        )
    if _TOKEN_BUDGET_PATTERN.search(content):
        issues.append(
            {
                "code": "wrong_bucket",
                "severity": "blocking",
                "title": "Token budget in instructions",
                "message": (
                    "Token limits are enforced by platform configuration, not instruction prose."
                ),
                "recommendation": (
                    "Remove token budget language from instructions and set token_budget "
                    "in Activity Settings."
                ),
                "fix_strategy": "relocate_to_settings",
                "suggested_target": "Settings",
            },
        )
    return issues
