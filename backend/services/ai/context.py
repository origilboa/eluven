"""Context assembly for AI calls (fixed layer order per 04-ai-patterns)."""

# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import boto3  # pyright: ignore[reportMissingTypeStubs]
import tiktoken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.config import settings
from core.logging import get_logger
from models.activity import ThreadQAQuestion, ThreadQAResponse
from models.instruction import (
    InstructionLevel,
    InstructionSet,
    InstructionVersion,
    TaskThreadTypeInstruction,
)
from models.kb import KBDocumentStatus, ThreadDocument, ThreadDocumentLoadStrategy
from models.memory import TaskMemoryEntry, TaskMemoryEntryType
from models.task import Task
from models.thread import MessageRole, Thread, ThreadMessage
from models.user import User
from services.document.chunker import DocumentChunker
from services.document.extractor import DocumentExtractor
from services.rag.retriever import ContextChunk, RAGRetriever
from services.storage import StorageService

logger = get_logger(__name__)

_STRUCTURED_MEMORY_ORDER = (
    TaskMemoryEntryType.FINDING,
    TaskMemoryEntryType.ASSUMPTION,
    TaskMemoryEntryType.GAP,
    TaskMemoryEntryType.REFERENCE,
)


@dataclass
class AssembledContext:
    """Bedrock-ready context following the instruction and content layer order."""

    system_blocks: list[dict[str, Any]]
    context_blocks: list[str]
    messages: list[dict[str, str]]
    current_message: str
    instruction_version: str | None = None
    compaction_performed: bool = False


class ContextAssembler:
    """Build AssembledContext for a Thread AI call."""

    def __init__(
        self,
        rag: RAGRetriever | None = None,
        storage: StorageService | None = None,
        extractor: DocumentExtractor | None = None,
        chunker: DocumentChunker | None = None,
    ) -> None:
        self._rag = rag or RAGRetriever()
        self._storage = storage or StorageService()
        self._extractor = extractor or DocumentExtractor()
        self._chunker = chunker or DocumentChunker()
        self._encoding = tiktoken.get_encoding("cl100k_base")

    async def assemble(
        self,
        thread: Thread,
        task: Task,
        message: str,
        session: AsyncSession,
    ) -> AssembledContext:
        """Assemble context in the mandated layer order."""
        self._last_compaction_performed = False
        owner = await session.get(User, thread.owner_id)
        working_language = (
            thread.working_language
            or task.working_language
            or (owner.default_working_language if owner else None)
            or "en"
        )

        platform_text = await self._instruction_for_level(
            session,
            InstructionLevel.PLATFORM,
            org_id=task.org_id,
            thread_type=thread.thread_type,
        )
        org_text = await self._instruction_for_level(
            session,
            InstructionLevel.ORG,
            org_id=task.org_id,
            owner_org_id=task.org_id,
            thread_type=thread.thread_type,
        )
        user_text = await self._instruction_for_level(
            session,
            InstructionLevel.USER,
            org_id=task.org_id,
            user_id=thread.owner_id,
            thread_type=thread.thread_type,
        )
        cluster_text = ""
        if task.cluster_id is not None:
            cluster_text = await self._instruction_for_level(
                session,
                InstructionLevel.CLUSTER,
                org_id=task.org_id,
                cluster_id=task.cluster_id,
                thread_type=thread.thread_type,
            )

        task_thread_text = await self._task_thread_instruction(session, task.id, thread.thread_type)
        task_level_text = await self._instruction_for_level(
            session,
            InstructionLevel.TASK,
            org_id=task.org_id,
            task_id=task.id,
            thread_type=thread.thread_type,
        )
        task_instruction_parts = [part for part in (task_level_text, task_thread_text) if part]
        task_instructions = "\n\n".join(task_instruction_parts)

        system_blocks: list[dict[str, Any]] = []
        if platform_text:
            system_blocks.append(_cached_text_block(platform_text))
        if org_text:
            system_blocks.append(_cached_text_block(org_text))
        if user_text:
            system_blocks.append(_cached_text_block(user_text))
        if cluster_text:
            system_blocks.append(_plain_text_block(cluster_text))
        if task_instructions:
            system_blocks.append(_plain_text_block(task_instructions))
        system_blocks.append(
            _plain_text_block(f"Working language: {working_language}"),
        )

        memory_block = await self._task_memory_block(session, task.id)
        thread_docs_block = await self._thread_documents_block(session, thread)
        rag_block = await self._rag_block(session, message, task.id, thread.id)
        qa_block = await self._qa_responses_block(session, thread.id)

        context_blocks = [
            block
            for block in (
                _task_context_block(task),
                memory_block,
                thread_docs_block,
                rag_block,
                qa_block,
            )
            if block
        ]

        history = await self._conversation_history(session, thread, task)
        instruction_version = thread.instruction_version

        logger.info(
            "context_assembled",
            thread_id=str(thread.id),
            task_id=str(task.id),
            system_block_count=len(system_blocks),
            context_block_count=len(context_blocks),
            history_message_count=len(history),
        )

        return AssembledContext(
            system_blocks=system_blocks,
            context_blocks=context_blocks,
            messages=history,
            current_message=message,
            instruction_version=instruction_version,
            compaction_performed=getattr(self, "_last_compaction_performed", False),
        )

    async def will_compact(self, session: AsyncSession, thread_id: UUID) -> bool:
        """Return True if the next assemble call will summarise older messages."""
        result = await session.execute(
            select(ThreadMessage)
            .where(ThreadMessage.thread_id == thread_id)
            .order_by(ThreadMessage.created_at.asc()),
        )
        all_messages = list(result.scalars().all())
        non_summary = [message for message in all_messages if not message.is_compaction_summary]
        if not non_summary:
            return False
        if any(message.is_compaction_summary for message in all_messages):
            return False
        token_count = sum(self._count_tokens(message.content) for message in non_summary)
        if token_count <= settings.context_history_token_limit:
            return False
        return len(non_summary) > settings.context_keep_recent_messages

    async def _instruction_for_level(
        self,
        session: AsyncSession,
        level: InstructionLevel,
        *,
        org_id: UUID,
        thread_type: str,
        owner_org_id: UUID | None = None,
        user_id: UUID | None = None,
        cluster_id: UUID | None = None,
        task_id: UUID | None = None,
    ) -> str:
        query = select(InstructionSet).where(InstructionSet.level == level)
        if owner_org_id is not None:
            query = query.where(InstructionSet.owner_org_id == owner_org_id)
        if user_id is not None:
            query = query.where(InstructionSet.user_id == user_id)
        if cluster_id is not None:
            query = query.where(InstructionSet.cluster_id == cluster_id)
        if task_id is not None:
            query = query.where(InstructionSet.task_id == task_id)
        if level == InstructionLevel.PLATFORM:
            query = query.where(InstructionSet.org_id == org_id)
        query = query.where(
            (InstructionSet.thread_type.is_(None))
            | (InstructionSet.thread_type == thread_type),
        )
        result = await session.execute(query.limit(1))
        instruction_set = result.scalar_one_or_none()
        if instruction_set is None or instruction_set.active_version_id is None:
            return ""
        version = await session.get(InstructionVersion, instruction_set.active_version_id)
        return version.content if version is not None else ""

    async def _task_thread_instruction(
        self,
        session: AsyncSession,
        task_id: UUID,
        thread_type: str,
    ) -> str:
        result = await session.execute(
            select(TaskThreadTypeInstruction)
            .where(
                TaskThreadTypeInstruction.task_id == task_id,
                TaskThreadTypeInstruction.thread_type == thread_type,
            )
            .limit(1),
        )
        row = result.scalar_one_or_none()
        return row.content if row is not None else ""

    async def _task_memory_block(self, session: AsyncSession, task_id: UUID) -> str:
        result = await session.execute(
            select(TaskMemoryEntry).where(
                TaskMemoryEntry.task_id == task_id,
                TaskMemoryEntry.is_deleted.is_(False),
            ),
        )
        entries = list(result.scalars().all())
        if not entries:
            return ""

        structured: list[TaskMemoryEntry] = []
        free_form: list[TaskMemoryEntry] = []
        for entry in entries:
            if entry.entry_type in _STRUCTURED_MEMORY_ORDER:
                structured.append(entry)
            else:
                free_form.append(entry)

        def sort_key(entry: TaskMemoryEntry) -> tuple[int, Any]:
            try:
                type_rank = _STRUCTURED_MEMORY_ORDER.index(entry.entry_type)
            except ValueError:
                type_rank = len(_STRUCTURED_MEMORY_ORDER)
            return (type_rank, entry.created_at)

        structured.sort(key=sort_key)
        free_form.sort(key=lambda entry: entry.created_at)

        lines: list[str] = ["## Task memory"]
        for entry in structured + free_form:
            confidence = (
                f" (confidence: {entry.confidence:.2f})" if entry.confidence is not None else ""
            )
            lines.append(f"- [{entry.entry_type.value}] {entry.content}{confidence}")
        return "\n".join(lines)

    async def _thread_documents_block(self, session: AsyncSession, thread: Thread) -> str:
        result = await session.execute(
            select(ThreadDocument).where(
                ThreadDocument.thread_id == thread.id,
                ThreadDocument.load_strategy == ThreadDocumentLoadStrategy.FULL_TEXT,
                ThreadDocument.status == KBDocumentStatus.READY,
            ),
        )
        documents = list(result.scalars().all())
        if not documents:
            return ""

        sections: list[str] = ["## Thread documents"]
        for document in documents:
            file_bytes = await asyncio.to_thread(
                self._storage.download_file,
                document.s3_key,
            )
            extracted = await asyncio.to_thread(
                self._extractor.extract,
                file_bytes,
                document.file_type,
                document.filename,
            )
            sections.append(f"### {document.filename}\n{extracted.text}")
        return "\n\n".join(sections)

    async def _rag_block(
        self,
        session: AsyncSession,
        query: str,
        task_id: UUID,
        thread_id: UUID,
    ) -> str:
        if not query.strip():
            return ""
        chunks = await self._rag.retrieve_for_context(
            query=query,
            task_id=task_id,
            thread_id=thread_id,
            session=session,
        )
        if not chunks:
            return ""
        return _format_rag_chunks(chunks)

    async def _qa_responses_block(self, session: AsyncSession, thread_id: UUID) -> str:
        result = await session.execute(
            select(ThreadQAResponse, ThreadQAQuestion)
            .join(
                ThreadQAQuestion,
                ThreadQAResponse.question_id == ThreadQAQuestion.id,
            )
            .where(ThreadQAResponse.thread_id == thread_id),
        )
        rows = list(result.all())
        if not rows:
            return ""

        lines = ["## Q&A responses"]
        for response, question in rows:
            question_text = question.question_text
            answer = response.response_text or ", ".join(response.response_options or [])
            lines.append(f"**Q:** {question_text}\n**A:** {answer}")
        return "\n\n".join(lines)

    async def _conversation_history(
        self,
        session: AsyncSession,
        thread: Thread,
        task: Task,
    ) -> list[dict[str, str]]:
        result = await session.execute(
            select(ThreadMessage)
            .where(ThreadMessage.thread_id == thread.id)
            .order_by(ThreadMessage.created_at.asc()),
        )
        all_messages = list(result.scalars().all())
        if not all_messages:
            return []

        non_summary = [message for message in all_messages if not message.is_compaction_summary]
        token_count = sum(self._count_tokens(message.content) for message in non_summary)

        self._last_compaction_performed = False

        if token_count <= settings.context_history_token_limit:
            return _messages_to_api_format(all_messages)

        existing_summary = next(
            (message for message in all_messages if message.is_compaction_summary),
            None,
        )
        keep_count = settings.context_keep_recent_messages
        if len(non_summary) <= keep_count:
            return _messages_to_api_format(all_messages)

        older = non_summary[:-keep_count]
        recent = non_summary[-keep_count:]

        if existing_summary is None:
            self._last_compaction_performed = True
            summary_text = await self._summarize_messages(older, thread, task)
            summary_message = ThreadMessage(
                thread_id=thread.id,
                role=MessageRole.SYSTEM,
                content=summary_text,
                is_compaction_summary=True,
            )
            session.add(summary_message)
            await session.flush()
            logger.info(
                "context_history_compacted",
                thread_id=str(thread.id),
                older_message_count=len(older),
                kept_message_count=len(recent),
            )
            ordered = [summary_message, *recent]
        else:
            ordered = [existing_summary, *recent]

        return _messages_to_api_format(ordered)

    async def _summarize_messages(
        self,
        messages: list[ThreadMessage],
        thread: Thread,
        task: Task,
    ) -> str:
        transcript = "\n".join(
            f"{message.role.value}: {message.content}" for message in messages
        )
        model_id = settings.default_bedrock_model_id
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Summarize the following conversation for use as context in "
                        "later messages. Preserve key findings, decisions, and open questions.\n\n"
                        f"{transcript}"
                    ),
                },
            ],
        }

        def _invoke() -> str:
            client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
            response = client.invoke_model(
                modelId=model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
            payload = json.loads(response["body"].read())
            content = payload.get("content", [])
            parts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            return "\n".join(parts).strip() or "Conversation summary unavailable."

        summary = await asyncio.to_thread(_invoke)
        logger.info(
            "context_compaction_summary_created",
            thread_id=str(thread.id),
            task_id=str(task.id),
            summarized_messages=len(messages),
        )
        return summary

    def _count_tokens(self, text: str) -> int:
        return len(self._encoding.encode(text))


def _cached_text_block(text: str) -> dict[str, Any]:
    return {
        "type": "text",
        "text": text,
        "cache_control": {"type": "ephemeral"},
    }


def _plain_text_block(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def _task_context_block(task: Task) -> str:
    lines = [
        "## Task context",
        f"Title: {task.title}",
        f"Module: {task.module_type}",
        f"Status: {task.status.value}",
    ]
    if task.description:
        lines.append(f"Description: {task.description}")
    if task.context:
        lines.append(f"Additional context: {json.dumps(task.context, ensure_ascii=False)}")
    return "\n".join(lines)


def _format_rag_chunks(chunks: list[ContextChunk]) -> str:
    lines = ["## Retrieved knowledge"]
    for index, item in enumerate(chunks, start=1):
        meta = item.source_metadata
        source = meta.get("filename") or meta.get("document_id") or "unknown"
        lines.append(
            f"[{index}] (score={item.similarity:.3f}, source={source})\n{item.chunk.content}",
        )
    return "\n\n".join(lines)


def _messages_to_api_format(messages: list[ThreadMessage]) -> list[dict[str, str]]:
    """Map DB messages to Bedrock roles (chronological; compaction summary first if present)."""
    api_messages: list[dict[str, str]] = []
    for message in messages:
        role = message.role.value
        if role not in ("user", "assistant"):
            role = "user"
        api_messages.append({"role": role, "content": message.content})
    return api_messages
