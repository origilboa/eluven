"""Shared helpers for document upload and integrity gates."""

from __future__ import annotations

from fastapi import HTTPException, status

from core.config import settings
from schemas.document_integrity import TaskIntegrityGateResponse


def validate_upload_size(size_bytes: int) -> None:
    """Reject uploads exceeding the configured maximum size."""
    if size_bytes > settings.document_max_upload_bytes:
        max_mb = settings.document_max_upload_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum upload size of {max_mb}MB",
        )


def raise_if_integrity_blocked(gate: TaskIntegrityGateResponse) -> None:
    """Raise HTTP 409 when task integrity warnings are unacknowledged."""
    if not gate.blocked:
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "integrity_acknowledgment_required",
            "message": "Document integrity warnings must be reviewed before continuing.",
            "unacknowledged_documents": [
                item.model_dump(mode="json") for item in gate.unacknowledged_documents
            ],
        },
    )
