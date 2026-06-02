"""Unit tests for plain-text document extraction."""

from services.document.extractor import DocumentExtractor


def test_extract_txt_without_unstructured() -> None:
    extractor = DocumentExtractor()
    result = extractor.extract(
        b"Hello from a plain text knowledge base document.",
        "txt",
        "sample.txt",
    )
    assert "Hello from a plain text" in result.text
    assert result.metadata["file_type"] == "txt"
