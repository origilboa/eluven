"""Section-aware document chunking with token overlap."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import tiktoken

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

_SECTION_HEADING_PATTERN = re.compile(r"(?m)^#{1,6}\s+.+$")


@dataclass
class ChunkData:
    """A single text chunk ready for embedding."""

    content: str
    chunk_index: int
    token_count: int
    metadata: dict[str, Any] = field(default_factory=lambda: dict[str, Any]())


class DocumentChunker:
    """Split document text into overlapping token-bounded chunks."""

    def __init__(
        self,
        *,
        chunk_size: int | None = None,
        overlap: int | None = None,
        encoding_name: str = "cl100k_base",
    ) -> None:
        self._chunk_size = chunk_size or settings.document_chunk_size_tokens
        self._overlap = overlap or settings.document_chunk_overlap_tokens
        self._encoding = tiktoken.get_encoding(encoding_name)

    def chunk(
        self,
        text: str,
        document_id: UUID | None,
        collection_id: UUID | None,
    ) -> list[ChunkData]:
        """Split text into section-aware overlapping chunks.

        Args:
            text: Full document text.
            document_id: Source document UUID stored in chunk metadata.
            collection_id: KB collection UUID stored in chunk metadata.

        Returns:
            Ordered list of ChunkData instances.
        """
        if not text.strip():
            logger.info("document_chunk_empty_text", document_id=str(document_id))
            return []

        sections = _split_sections(text)
        chunk_texts: list[str] = []
        for section in sections:
            chunk_texts.extend(
                self._chunk_section(section, self._chunk_size, self._overlap),
            )

        base_metadata: dict[str, Any] = {}
        if document_id is not None:
            base_metadata["document_id"] = str(document_id)
        if collection_id is not None:
            base_metadata["collection_id"] = str(collection_id)

        chunks: list[ChunkData] = []
        for index, content in enumerate(chunk_texts):
            token_count = len(self._encoding.encode(content))
            chunk_metadata = {
                **base_metadata,
                "section_aware": True,
            }
            chunks.append(
                ChunkData(
                    content=content,
                    chunk_index=index,
                    token_count=token_count,
                    metadata=chunk_metadata,
                ),
            )

        logger.info(
            "document_chunk_complete",
            document_id=str(document_id),
            collection_id=str(collection_id),
            chunk_count=len(chunks),
            section_count=len(sections),
        )
        return chunks

    def count_tokens(self, text: str) -> int:
        """Return token count for a text string."""
        return len(self._encoding.encode(text))

    def _chunk_section(self, text: str, chunk_size: int, overlap: int) -> list[str]:
        """Create overlapping chunks within a single section."""
        tokens = self._encoding.encode(text)
        if len(tokens) <= chunk_size:
            return [text.strip()] if text.strip() else []

        step = max(chunk_size - overlap, 1)
        chunks: list[str] = []
        for start in range(0, len(tokens), step):
            end = min(start + chunk_size, len(tokens))
            piece = self._encoding.decode(tokens[start:end]).strip()
            if piece:
                chunks.append(piece)
            if end >= len(tokens):
                break
        return chunks


def _split_sections(text: str) -> list[str]:
    """Split text on markdown headings; fall back to paragraph blocks."""
    stripped = text.strip()
    if not stripped:
        return []

    if _SECTION_HEADING_PATTERN.search(stripped):
        parts = re.split(r"(?m)(?=^#{1,6}\s)", stripped)
        return [part.strip() for part in parts if part.strip()]

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", stripped) if p.strip()]
    if not paragraphs:
        return [stripped]

    sections: list[str] = []
    current: list[str] = []
    for paragraph in paragraphs:
        if _SECTION_HEADING_PATTERN.match(paragraph):
            if current:
                sections.append("\n\n".join(current))
                current = []
            current.append(paragraph)
        else:
            current.append(paragraph)
    if current:
        sections.append("\n\n".join(current))
    return sections
