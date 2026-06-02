"""Unit tests for Word export generation."""

from uuid import uuid4

from models.memory import TaskMemoryEntry, TaskMemoryEntryType
from models.task import Task, TaskStatus
from models.thread import Thread, ThreadStatus
from services.export.word_exporter import build_task_word_export


def test_build_task_word_export_includes_memory_and_threads() -> None:
    task_id = uuid4()
    thread_id = uuid4()
    task = Task(
        id=task_id,
        org_id=uuid4(),
        owner_id=uuid4(),
        title="Sample Review",
        module_type="external_paper_review",
        status=TaskStatus.ACTIVE,
    )
    memory = TaskMemoryEntry(
        id=uuid4(),
        org_id=task.org_id,
        task_id=task_id,
        thread_id=thread_id,
        entry_type=TaskMemoryEntryType.FINDING,
        content="Strong methodology section.",
        confidence=0.9,
    )
    thread = Thread(
        id=thread_id,
        org_id=task.org_id,
        task_id=task_id,
        owner_id=task.owner_id,
        title="Initial Read",
        thread_type="initial_read",
        status=ThreadStatus.ACTIVE,
    )

    content = build_task_word_export(task, [memory], [thread])

    assert content.startswith(b"PK")
    assert len(content) > 1000
