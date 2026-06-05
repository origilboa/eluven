"""Structured instruction integrity checks via Bedrock."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import boto3  # pyright: ignore[reportMissingTypeStubs]
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logging import get_logger
from models.user import User
from schemas.instruction_assistant import (
    ClarifyingQuestion,
    InstructionAssistantScope,
    InstructionIntegrityCheckResponse,
    InstructionIntegrityIssue,
)
from services.instructions.authoring_context import InstructionAuthoringContext
from services.instructions.integrity_gate import (
    compute_content_hash,
    deterministic_integrity_issues,
    issue_approval_token,
    scope_key_from_assistant_scope,
)

logger = get_logger(__name__)

_JSON_BLOCK_PATTERN = re.compile(r"\{[\s\S]*\}", re.MULTILINE)


class InstructionIntegrityChecker:
    """Run deterministic + LLM integrity checks for instruction drafts."""

    def __init__(
        self,
        *,
        context_builder: InstructionAuthoringContext | None = None,
        bedrock_client: Any | None = None,
    ) -> None:
        self._context_builder = context_builder or InstructionAuthoringContext()
        self._bedrock = bedrock_client or boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
        )

    async def check(
        self,
        session: AsyncSession,
        *,
        user: User,
        scope: InstructionAssistantScope,
        draft_content: str,
        locale: str,
    ) -> InstructionIntegrityCheckResponse:
        """Return pass/fail with rich issues and approval token on pass."""
        content_hash = compute_content_hash(draft_content)
        scope_key = scope_key_from_assistant_scope(scope)

        det_raw = deterministic_integrity_issues(draft_content)
        det_issues = [InstructionIntegrityIssue(**item) for item in det_raw]
        blocking_det = [issue for issue in det_issues if issue.severity == "blocking"]
        if blocking_det:
            return self._fail_response(
                content_hash=content_hash,
                summary="Blocking issues found in instruction draft.",
                issues=det_issues,
            )

        context = await self._context_builder.build(
            session,
            scope=scope,
            user=user,
            draft_content=draft_content,
            chat_messages=[],
            locale=locale,
            integrity_review=True,
        )

        llm_result = await self._llm_check(context.system_text, draft_content, locale)
        llm_issues = [
            InstructionIntegrityIssue(**issue)
            for issue in llm_result.get("issues", [])
            if isinstance(issue, dict)
        ]
        questions = [
            ClarifyingQuestion(**question)
            for question in llm_result.get("clarifying_questions", [])
            if isinstance(question, dict)
        ]

        all_issues = det_issues + llm_issues
        blocking = [issue for issue in all_issues if issue.severity == "blocking"]
        status = llm_result.get("status", "fail" if blocking else "pass")
        if blocking:
            status = "fail"

        summary = str(
            llm_result.get("summary")
            or (
                "No blocking issues found."
                if status == "pass"
                else "Blocking issues found in instruction draft."
            ),
        )

        if status == "pass" and not blocking:
            token, expires_at = issue_approval_token(
                user_id=str(user.id),
                scope_key=scope_key,
                content_hash=content_hash,
            )
            logger.info(
                "instruction_integrity_check_passed",
                user_id=str(user.id),
                level=scope.level,
                content_hash=content_hash[:16],
            )
            return InstructionIntegrityCheckResponse(
                status="pass",
                summary=summary,
                content_hash=content_hash,
                issues=all_issues,
                clarifying_questions=questions,
                approval_token=token,
                expires_at=datetime.fromtimestamp(expires_at, tz=UTC),
            )

        logger.info(
            "instruction_integrity_check_failed",
            user_id=str(user.id),
            level=scope.level,
            issue_count=len(blocking),
        )
        return self._fail_response(
            content_hash=content_hash,
            summary=summary,
            issues=all_issues,
            clarifying_questions=questions,
        )

    async def _llm_check(
        self,
        system_text: str,
        draft_content: str,
        locale: str,
    ) -> dict[str, Any]:
        prompt = (
            "Run a full instruction integrity review on the editable-layer draft. "
            "Compare against inherited instructions in the system context. "
            "Return ONLY valid JSON with this shape:\n"
            "{\n"
            '  "status": "pass" or "fail",\n'
            '  "summary": "string",\n'
            '  "issues": [{"code":"...","severity":"blocking|warning","title":"...",'
            '"message":"...","excerpt":"...","conflicting_level":"...|null",'
            '"recommendation":"...","suggested_target":"...|null",'
            '"fix_strategy":"remove_excerpt|move_to_layer|rephrase_as_delta|'
            'relocate_to_settings|relocate_to_prompts|ask_user",'
            '"needs_user_input":false}],\n'
            '  "clarifying_questions": [{"id":"q1","prompt":"...","why_needed":"..."}]\n'
            "}\n"
            f"Working language for messages: {locale}. "
            "Any blocking issue => status fail."
        )
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "system": system_text,
            "messages": [{"role": "user", "content": prompt}],
        }
        try:
            response = self._bedrock.invoke_model(
                modelId=settings.instruction_authoring_model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json",
            )
            body = json.loads(response["body"].read())
            text_parts = [
                block.get("text", "")
                for block in body.get("content", [])
                if block.get("type") == "text"
            ]
            raw = "".join(text_parts)
            match = _JSON_BLOCK_PATTERN.search(raw)
            if not match:
                return {"status": "fail", "summary": "Integrity check could not parse model output.", "issues": []}
            return json.loads(match.group())
        except Exception as exc:
            logger.warning("instruction_integrity_llm_failed", error=str(exc))
            return {
                "status": "fail",
                "summary": "Integrity check failed due to an AI service error. Try again.",
                "issues": [],
            }

    @staticmethod
    def _fail_response(
        *,
        content_hash: str,
        summary: str,
        issues: list[InstructionIntegrityIssue],
        clarifying_questions: list[ClarifyingQuestion] | None = None,
    ) -> InstructionIntegrityCheckResponse:
        return InstructionIntegrityCheckResponse(
            status="fail",
            summary=summary,
            content_hash=content_hash,
            issues=issues,
            clarifying_questions=clarifying_questions or [],
            approval_token=None,
            expires_at=None,
        )
