"""Document text extraction via Unstructured.io."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any

from unstructured.documents.elements import Table
from unstructured.partition.csv import partition_csv
from unstructured.partition.doc import partition_doc
from unstructured.partition.docx import partition_docx
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.text import partition_text
from unstructured.partition.xlsx import partition_xlsx

from core.logging import get_logger
from services.document.constants import SUPPORTED_FILE_TYPES

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
        """Extract text, tables, and metadata from a document.

        Args:
            file_bytes: Raw file content.
            file_type: File extension without dot (e.g. pdf, docx).
            filename: Original filename for format detection.

        Returns:
            ExtractedDocument with combined text, table dicts, and metadata.

        Raises:
            ValueError: If file_type is not supported.
        """
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

        buffer = io.BytesIO(file_bytes)
        elements = self._partition(buffer, normalized_type, filename)

        text_parts: list[str] = []
        tables: list[dict[str, Any]] = []
        element_types: list[str] = []

        for element in elements:
            element_type = getattr(element, "category", type(element).__name__)
            element_types.append(str(element_type))
            if isinstance(element, Table):
                table_entry: dict[str, Any] = {
                    "text": str(element),
                    "metadata": _element_metadata(element),
                }
                html = getattr(element.metadata, "text_as_html", None)
                if html:
                    table_entry["html"] = html
                tables.append(table_entry)
            else:
                snippet = str(element).strip()
                if snippet:
                    text_parts.append(snippet)

        text = "\n\n".join(text_parts)
        metadata: dict[str, Any] = {
            "filename": filename,
            "file_type": normalized_type,
            "size_bytes": size_bytes,
            "element_count": len(elements),
            "element_types": element_types,
        }

        logger.info(
            "document_extract_complete",
            file_type=normalized_type,
            size_bytes=size_bytes,
            text_length=len(text),
            table_count=len(tables),
        )

        return ExtractedDocument(text=text, tables=tables, metadata=metadata)

    def _partition(
        self,
        buffer: io.BytesIO,
        file_type: str,
        filename: str,
    ) -> list[Any]:
        """Route to the appropriate Unstructured partitioner."""
        if file_type == "pdf":
            return partition_pdf(file=buffer, file_filename=filename)
        if file_type == "docx":
            return partition_docx(file=buffer, file_filename=filename)
        if file_type == "doc":
            return partition_doc(file=buffer, file_filename=filename)
        if file_type == "txt":
            return partition_text(file=buffer, file_filename=filename)
        if file_type == "tex":
            return partition_text(file=buffer, file_filename=filename)
        if file_type == "xlsx":
            return partition_xlsx(file=buffer, file_filename=filename)
        if file_type == "csv":
            return partition_csv(file=buffer, file_filename=filename)
        raise ValueError(f"Unsupported file type: {file_type}")


def _element_metadata(element: Any) -> dict[str, Any]:
    """Serialize Unstructured element metadata to a plain dict."""
    metadata = getattr(element, "metadata", None)
    if metadata is None:
        return {}
    if hasattr(metadata, "to_dict"):
        return dict(metadata.to_dict())
    return {}
