"""Schemas for document integrity scanning and acknowledgment."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class IntegrityFindingType(str, Enum):
    """Typed integrity findings from document scans."""

    PROMPT_INJECTION_PATTERN = "prompt_injection_pattern"
    HIDDEN_FORMATTING = "hidden_formatting"
    UNICODE_ANOMALY = "unicode_anomaly"
    STRUCTURAL_MIMICRY = "structural_mimicry"
    FILENAME_SUSPICIOUS = "filename_suspicious"
    CONTEXT_STUFFING = "context_stuffing"
    INSTRUCTION_DENSITY = "instruction_density"
    RAG_BAIT = "rag_bait"


class IntegrityStatus(str, Enum):
    """Aggregate integrity status for a document."""

    CLEAN = "clean"
    WARNING = "warning"
    REVIEW_REQUIRED = "review_required"


class IntegrityAcknowledgmentChoice(str, Enum):
    """User choice when acknowledging an integrity warning."""

    PROCEED = "proceed"
    CANCEL = "cancel"


class IntegrityFinding(BaseModel):
    """Single integrity finding (no raw matched text in API responses)."""

    finding_type: IntegrityFindingType
    count: int = Field(ge=1)
    detail: str | None = None


class IntegrityReport(BaseModel):
    """Structured integrity scan result persisted on document rows."""

    status: IntegrityStatus
    findings: list[IntegrityFinding] = Field(default_factory=list)
    content_hash: str
    scanned_at: datetime
    extract_token_count: int | None = None

    def to_storage(self) -> dict[str, Any]:
        """Serialize for JSONB storage."""
        return self.model_dump(mode="json")

    @classmethod
    def from_storage(cls, data: dict[str, Any] | None) -> IntegrityReport | None:
        if not data:
            return None
        return cls.model_validate(data)


class IntegrityReportSummary(BaseModel):
    """Public integrity summary on document API responses."""

    status: IntegrityStatus
    findings: list[IntegrityFinding] = Field(default_factory=list)
    content_hash: str | None = None
    acknowledged: bool = False
    acknowledged_at: datetime | None = None


class AcknowledgeIntegrityRequest(BaseModel):
    """Request body for integrity warning acknowledgment."""

    choice: IntegrityAcknowledgmentChoice


class TaskIntegrityDocumentSummary(BaseModel):
    """Document blocking AI until acknowledged."""

    document_id: UUID
    filename: str
    source: str
    integrity_status: IntegrityStatus
    findings: list[IntegrityFinding] = Field(default_factory=list)


class TaskIntegrityGateResponse(BaseModel):
    """Task-level integrity gate for AI and workflow operations."""

    blocked: bool
    unacknowledged_documents: list[TaskIntegrityDocumentSummary] = Field(default_factory=list)
