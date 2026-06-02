"""Unit tests for MVP lightweight document extraction (ADR 002)."""

from io import BytesIO

from docx import Document

from services.document.extractor import DocumentExtractor

_MINIMAL_PDF = b"""%PDF-1.1
1 0 obj<< /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj<< /Type /Page /MediaBox [0 0 612 792] /Contents 4 0 R
/Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj<< /Length 44 >> stream
BT /F1 12 Tf 100 700 Td (Hello PDF) Tj ET
endstream endobj
5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000274 00000 n
0000000370 00000 n
trailer<< /Size 6 /Root 1 0 R >>
startxref
459
%%EOF"""


def _make_docx_bytes(*paragraphs: str) -> bytes:
    document = Document()
    for text in paragraphs:
        document.add_paragraph(text)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_extract_txt() -> None:
    extractor = DocumentExtractor()
    result = extractor.extract(
        b"Hello from a plain text knowledge base document.",
        "txt",
        "sample.txt",
    )
    assert "Hello from a plain text" in result.text
    assert result.metadata["file_type"] == "txt"


def test_extract_pdf_text_layer() -> None:
    extractor = DocumentExtractor()
    result = extractor.extract(_MINIMAL_PDF, "pdf", "sample.pdf")
    assert "Hello PDF" in result.text
    assert result.metadata["extractor"] == "pdfminer.six"
    assert result.metadata["ocr"] is False


def test_extract_docx() -> None:
    extractor = DocumentExtractor()
    docx_bytes = _make_docx_bytes("Introduction paragraph.", "Methods follow here.")
    result = extractor.extract(docx_bytes, "docx", "paper.docx")
    assert "Introduction paragraph." in result.text
    assert "Methods follow here." in result.text
    assert result.metadata["extractor"] == "python-docx"


def test_extract_csv() -> None:
    extractor = DocumentExtractor()
    result = extractor.extract(
        b"col_a,col_b\nvalue1,value2\n",
        "csv",
        "data.csv",
    )
    assert "value1" in result.text
    assert "value2" in result.text
    assert result.metadata["extractor"] == "csv"
