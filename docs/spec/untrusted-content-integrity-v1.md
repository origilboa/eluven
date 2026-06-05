# Untrusted content integrity v1

**Scope:** Cross-application protection against document-based prompt injection and related integrity risks.

## Trust model

| Source | Trust | Handling |
|--------|-------|----------|
| InstructionLayer (platform → thread) | Trusted | Bedrock system blocks |
| TaskDocument / KBDocument text | Untrusted | Integrity scan + XML wrapper in context |
| RAG chunks | Untrusted | Wrapper in context assembly |
| Task metadata / tags | Untrusted | Wrapper in context assembly |
| TaskMemory | Derived | Platform directive: re-verify against documents |

## Detection (`DocumentIntegrityService`)

Finding types: `prompt_injection_pattern`, `hidden_formatting`, `unicode_anomaly`, `structural_mimicry`, `filename_suspicious`, `context_stuffing`, `instruction_density`, `rag_bait`.

Runs at document processing time for `TaskDocument` and `KBDocument`. Stores `integrity_report` JSONB and `content_hash` (SHA-256 of extracted text).

## Enforcement

When status is `warning` or `review_required`:

1. Prominent UI warning on task documents panel
2. AI stream and workflow start return HTTP 409 until user acknowledges per document
3. User choices: **proceed** (records acknowledgment) or **cancel**
4. Re-upload / reprocess clears acknowledgment when `content_hash` changes

## API

- `GET /api/v1/tasks/{task_id}/integrity-gate`
- `POST /api/v1/tasks/{task_id}/documents/{document_id}/integrity-acknowledge`
- `POST /api/v1/kb/collections/{collection_id}/documents/{document_id}/integrity-acknowledge`

## Configuration (environment)

- `DOCUMENT_MAX_UPLOAD_BYTES` (default 50MB)
- `INTEGRITY_MIN_FONT_HALF_POINTS`
- `INTEGRITY_STUFFING_MIN_CHARS`, `INTEGRITY_STUFFING_HIDDEN_CHARS`, `INTEGRITY_STUFFING_MAX_CHARS`
- `INTEGRITY_IMPERATIVE_DENSITY_THRESHOLD`
- `INTEGRITY_WARNING_THRESHOLD`

## Future modules

New modules inherit protection automatically when using `TaskDocument`, `ContextAssembler`, and `DocumentProcessor`. Do not add module-specific injection logic.
