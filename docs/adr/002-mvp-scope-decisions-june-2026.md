# ADR 002: MVP scope decisions — document pipeline, SPR, Word export

**Status:** Accepted  
**Date:** 2026-06-02  
**Context:** MVP completeness audit — three blocking decisions before internal sign-off

## Decision 1 — Document indexing (PDF / DOCX)

**Choice:** Lightweight extractors in the Docker image — **no** `unstructured_inference` ML stack for MVP.

| Format | MVP extractor | Notes |
|--------|---------------|-------|
| `.txt`, `.tex` | UTF-8 decode | Already in production |
| `.pdf` | `pdfminer.six` (text layer) | Fast, no ML; no OCR for scanned PDFs |
| `.docx` | `python-docx` | Paragraphs + table cell text |
| `.xlsx`, `.csv` | `openpyxl` / `csv` | Tabular text for RAG |
| `.doc` | LibreOffice headless → text | Legacy Word; already in runtime image |

**Deferred post-MVP:** Unstructured hi-res PDF, OCR, rich HTML table metadata, `unstructured_inference` in Docker.

**Rationale:** ECS tasks have no NAT; ML deps inflate image size and build time. EPR validation needs **text-layer PDFs** (typical publisher manuscripts), not scanned images.

## Decision 2 — SPR module scope

**Choice:** **Minimal SPR** for MVP internal validation.

**In scope:**

- Assignment Cluster (`cluster_type: assignment`)
- Submission Tasks under an Assignment
- Assignments list + cluster detail + create submission
- Per-submission threads, memory, workflows (same as any Task)

**Out of scope for MVP:**

- Batch grading dashboard across all submissions
- Aggregate grade book / class statistics UI
- Side-by-side submission comparison view
- Export of combined class report

**Rationale:** Assignment/Submission hierarchy satisfies §8.1 domain model. Batch UX is high effort and not required to validate the core SPR review loop with internal users.

## Decision 3 — Word export shape

**Choice:** **Module-aware generic export** — not full publisher report templates.

- **EPR:** Title, metadata, sections ordered for paper review (Findings → Assumptions → Gaps → References → Thread summary)
- **SPR:** Title, metadata, sections ordered for student feedback (Findings → Assumptions → Gaps → References → Thread summary with thread types labeled)

Same memory categories; cover heading and section intro text differ by `module_type`. No custom Word styles per publisher.

**Deferred:** Decision 28 report templates, Hebrew export locale, collaborator export permissions.

## Consequences

- Scanned PDFs without a text layer will fail indexing — acceptable for MVP; document in validation checklist
- SPR users create submissions one at a time; no batch view until Phase 1
- Word export is sufficient for internal review handoff, not publisher submission format
