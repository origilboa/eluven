"""Wrap untrusted content for safe inclusion in AI context."""

from __future__ import annotations

from typing import Literal

from schemas.document_integrity import IntegrityReport, IntegrityStatus

UntrustedSourceType = Literal[
    "task_document",
    "kb_chunk",
    "task_metadata",
    "rag",
]

_TAG_BY_SOURCE: dict[UntrustedSourceType, str] = {
    "task_document": "untrusted_document",
    "kb_chunk": "untrusted_reference",
    "task_metadata": "untrusted_metadata",
    "rag": "untrusted_reference",
}


def wrap_untrusted_block(
    content: str,
    *,
    source_type: UntrustedSourceType,
    source_id: str,
    filename: str | None = None,
    integrity_report: IntegrityReport | None = None,
) -> str:
    """Wrap untrusted text in explicit data-boundary tags for the model."""
    if not content.strip():
        return ""

    tag = _TAG_BY_SOURCE[source_type]
    attrs = [f'source_id="{source_id}"']
    if filename:
        attrs.append(f'filename="{_escape_attr(filename)}"')
    if integrity_report is not None:
        attrs.append(f'integrity_status="{integrity_report.status.value}"')

    attr_str = " ".join(attrs)
    header = f"<{tag} {attr_str}>"
    footer = f"</{tag}>"

    warning = ""
    if integrity_report is not None and integrity_report.status != IntegrityStatus.CLEAN:
        finding_types = ", ".join(
            sorted({finding.finding_type.value for finding in integrity_report.findings}),
        )
        warning = (
            f"[Integrity scan: {integrity_report.status.value}"
            f"{f' — {finding_types}' if finding_types else ''}]\n"
        )

    return f"{header}\n{warning}{content.strip()}\n{footer}"


def _escape_attr(value: str) -> str:
    return value.replace('"', "'")
