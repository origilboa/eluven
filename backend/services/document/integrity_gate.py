"""Task-level integrity gates for AI and workflow operations."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.kb import (
    KBCollectionAttachment,
    KBDocument,
    KBDocumentStatus,
    TaskDocument,
)
from models.task import Task
from schemas.document_integrity import (
    IntegrityFinding,
    IntegrityReport,
    IntegrityReportSummary,
    IntegrityStatus,
    TaskIntegrityDocumentSummary,
    TaskIntegrityGateResponse,
)


def integrity_summary_for_document(
    *,
    integrity_report: dict | None,
    integrity_acknowledged_hash: str | None,
    integrity_acknowledged_at: object | None = None,
) -> IntegrityReportSummary | None:
    """Build API integrity summary from stored document fields."""
    report = IntegrityReport.from_storage(integrity_report)
    if report is None:
        return None

    acknowledged = (
        integrity_acknowledged_hash is not None
        and integrity_acknowledged_hash == report.content_hash
    )
    acknowledged_at = integrity_acknowledged_at if acknowledged else None
    return IntegrityReportSummary(
        status=report.status,
        findings=report.findings,
        content_hash=report.content_hash,
        acknowledged=acknowledged,
        acknowledged_at=acknowledged_at,  # type: ignore[arg-type]
    )


def document_requires_acknowledgment(
    *,
    integrity_report: dict | None,
    integrity_acknowledged_hash: str | None,
) -> bool:
    """Return True when document has warnings and no valid acknowledgment."""
    report = IntegrityReport.from_storage(integrity_report)
    if report is None or report.status == IntegrityStatus.CLEAN:
        return False
    return integrity_acknowledged_hash != report.content_hash


async def evaluate_task_integrity_gate(
    session: AsyncSession,
    task_id: UUID,
) -> TaskIntegrityGateResponse:
    """Return whether AI/workflow operations should be blocked for a task."""
    unacknowledged: list[TaskIntegrityDocumentSummary] = []

    task_docs_result = await session.execute(
        select(TaskDocument).where(
            TaskDocument.task_id == task_id,
            TaskDocument.status == KBDocumentStatus.READY,
        ),
    )
    for document in task_docs_result.scalars().all():
        if not document_requires_acknowledgment(
            integrity_report=document.integrity_report,
            integrity_acknowledged_hash=document.integrity_acknowledged_hash,
        ):
            continue
        report = IntegrityReport.from_storage(document.integrity_report)
        unacknowledged.append(
            _document_summary(
                document_id=document.id,
                filename=document.filename,
                source="task_document",
                report=report,
            ),
        )

    kb_docs = await _kb_documents_for_task(session, task_id)
    for document in kb_docs:
        if not document_requires_acknowledgment(
            integrity_report=document.integrity_report,
            integrity_acknowledged_hash=document.integrity_acknowledged_hash,
        ):
            continue
        report = IntegrityReport.from_storage(document.integrity_report)
        unacknowledged.append(
            _document_summary(
                document_id=document.id,
                filename=document.filename,
                source="kb_document",
                report=report,
            ),
        )

    return TaskIntegrityGateResponse(
        blocked=len(unacknowledged) > 0,
        unacknowledged_documents=unacknowledged,
    )


async def _kb_documents_for_task(
    session: AsyncSession,
    task_id: UUID,
) -> list[KBDocument]:
    task = await session.get(Task, task_id)
    if task is None:
        return []

    collection_ids: list[UUID] = []
    task_attachments = await session.execute(
        select(KBCollectionAttachment.collection_id).where(
            KBCollectionAttachment.entity_type == "task",
            KBCollectionAttachment.entity_id == task_id,
        ),
    )
    collection_ids.extend(task_attachments.scalars().all())

    if task.cluster_id is not None:
        cluster_attachments = await session.execute(
            select(KBCollectionAttachment.collection_id).where(
                KBCollectionAttachment.entity_type == "cluster",
                KBCollectionAttachment.entity_id == task.cluster_id,
            ),
        )
        collection_ids.extend(cluster_attachments.scalars().all())

    if not collection_ids:
        return []

    result = await session.execute(
        select(KBDocument).where(
            KBDocument.collection_id.in_(collection_ids),
            KBDocument.status == KBDocumentStatus.READY,
            KBDocument.is_deleted.is_(False),
            KBDocument.is_active.is_(True),
        ),
    )
    return list(result.scalars().all())


def _document_summary(
    *,
    document_id: UUID,
    filename: str,
    source: str,
    report: IntegrityReport | None,
) -> TaskIntegrityDocumentSummary:
    findings: list[IntegrityFinding] = report.findings if report is not None else []
    status = report.status if report is not None else IntegrityStatus.WARNING
    return TaskIntegrityDocumentSummary(
        document_id=document_id,
        filename=filename,
        source=source,
        integrity_status=status,
        findings=findings,
    )
