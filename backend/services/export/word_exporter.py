"""Generate Word (.docx) exports from Task memory and thread summaries."""

from __future__ import annotations

from io import BytesIO

from docx import Document
from docx.shared import Pt

from models.memory import TaskMemoryEntry, TaskMemoryEntryType
from models.task import Task
from models.thread import Thread


def _add_memory_section(
    doc: Document,
    heading: str,
    entries: list[TaskMemoryEntry],
) -> None:
    if not entries:
        return
    doc.add_heading(heading, level=2)
    for entry in entries:
        paragraph = doc.add_paragraph(entry.content)
        paragraph.style = "List Bullet"
        if entry.confidence is not None:
            doc.add_paragraph(
                f"Confidence: {entry.confidence:.0%}",
                style="Intense Quote",
            )


def build_task_word_export(
    task: Task,
    memory_entries: list[TaskMemoryEntry],
    threads: list[Thread],
) -> bytes:
    """Build a Word document summarizing task memory and threads."""
    doc = Document()
    title = doc.add_heading(task.title, level=0)
    title.runs[0].font.size = Pt(24)

    doc.add_paragraph(f"Module: {task.module_type}")
    doc.add_paragraph(f"Status: {task.status.value}")

    grouped: dict[TaskMemoryEntryType, list[TaskMemoryEntry]] = {
        TaskMemoryEntryType.FINDING: [],
        TaskMemoryEntryType.ASSUMPTION: [],
        TaskMemoryEntryType.GAP: [],
        TaskMemoryEntryType.REFERENCE: [],
    }
    for entry in memory_entries:
        grouped[entry.entry_type].append(entry)

    doc.add_heading("Task Memory", level=1)
    _add_memory_section(doc, "Findings", grouped[TaskMemoryEntryType.FINDING])
    _add_memory_section(doc, "Assumptions", grouped[TaskMemoryEntryType.ASSUMPTION])
    _add_memory_section(doc, "Gaps", grouped[TaskMemoryEntryType.GAP])
    _add_memory_section(doc, "References", grouped[TaskMemoryEntryType.REFERENCE])

    if not memory_entries:
        doc.add_paragraph("No memory entries recorded yet.")

    if threads:
        doc.add_heading("Threads", level=1)
        for thread in threads:
            doc.add_heading(thread.title, level=2)
            doc.add_paragraph(f"Type: {thread.thread_type}")
            doc.add_paragraph(f"Status: {thread.status.value}")

    buffer = BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
