"""Document text extraction — lightweight MVP path (ADR 002)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.logging import get_logger
from services.document.constants import SUPPORTED_FILE_TYPES
from services.document import lightweight_extractors as lw

logger = get_logger(__name__)


@dataclass
class ExtractedDocument:
    """Structured output from document extraction."""

    text: str
    tables: list[dict[str, Any]] = field(default_factory=lambda: list[dict[str, Any]]())
    metadata: dict[str, Any] = field(default_factory=lambda: dict[str, Any]())


class DocumentExtractor:
    """Extract plain text and tables from supported document formats."""

    def extract(self, file_bytes: bytes, file_type: str, filename: str) -> ExtractedDocument:
        """Extract text, tables, and metadata from a document."""
        normalized_type = file_type.lower().lstrip(".")
        size_bytes = len(file_bytes)

        logger.info(
            "document_extract_started",
            file_type=normalized_type,
            filename=filename,
            size_bytes=size_bytes,
        )

        if normalized_type not in SUPPORTED_FILE_TYPES:
            raise ValueError(f"Unsupported file type: {file_type}")

        text: str
        tables: list[dict[str, Any]]
        metadata: dict[str, Any]

        if normalized_type in {"txt", "tex"}:
            text, tables, metadata = lw.extract_txt_or_tex(file_bytes, filename, normalized_type)
        elif normalized_type == "pdf":
            text, tables, metadata = lw.extract_pdf(file_bytes, filename)
        elif normalized_type == "docx":
            text, tables, metadata = lw.extract_docx(file_bytes, filename)
        elif normalized_type == "doc":
            text, tables, metadata = lw.extract_doc(file_bytes, filename)
        elif normalized_type == "xlsx":
            text, tables, metadata = lw.extract_xlsx(file_bytes, filename)
        elif normalized_type == "csv":
            text, tables, metadata = lw.extract_csv(file_bytes, filename)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        logger.info(
            "document_extract_complete",
            file_type=normalized_type,
            size_bytes=size_bytes,
            text_length=len(text),
            table_count=len(tables),
            extractor=metadata.get("extractor"),
        )

        return ExtractedDocument(text=text, tables=tables, metadata=metadata)
