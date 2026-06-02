# Open questions — post MVP audit (June 2026)

Tracked after MVP completeness implementation. Resolve before external launch or next major milestone.

**MVP sign-off plan:** [validation/mvp-signoff-plan.md](validation/mvp-signoff-plan.md)  
**Demo sample data:** [validation/sample-data.md](validation/sample-data.md)

## Resolved (June 2026) — see [ADR 002](/docs/adr/002-mvp-scope-decisions-june-2026.md)

| Decision | Choice |
|----------|--------|
| PDF/DOCX indexing | Lightweight extractors (`pdfminer.six`, `python-docx`, LibreOffice for `.doc`) — no ML stack |
| SPR MVP scope | Minimal: Assignment + Submission hierarchy only; no batch grading dashboard |
| Word export | Module-aware generic export (EPR vs SPR headings); not full publisher templates |

---
## Product / validation

1. **EPR end-to-end with real PDF** — ActivityLibrary, Word export, and workflow UI exist; has a reviewer completed one full paper review task and signed off on output quality?
2. **SPR end-to-end** — Assignment/submission UI and API exist; **MVP scope is minimal** (no batch grading dashboard — see ADR 002). Validate one Assignment → Submission → thread review path.
3. **Master instruction quality** — Only `initial_read` and `final_recommendation` platform seeds in migration 006; remaining EPR/SPR thread types need drafted instructions and quality testing.
4. **Hebrew/RTL production validation** — i18n scaffold and logical CSS in place; full UI pass in `he` locale not documented.
5. **UX friction log** — MVP success criterion §8.3; no structured friction notes yet from internal users.

## Technical

6. **PDF/DOCX indexing in production** — **Decided + validated (ADR 002):** lightweight extractors deployed; txt, pdf, and docx fixtures pass `scripts/validate_mvp_kb_rag.py` on production (2026-06-02).
7. **Rate limiting (10 AI calls/min)** — Spec §4; not implemented.
8. **Concurrent workflow limit (3/user)** — Not enforced.
9. ~~**Thread document upload UI**~~ — Task/thread document panels added (upload, list, download). See task detail **Paper under review** vs **Reference knowledge base**.
10. **Instruction Studio levels 4–5** — **Cluster + task UI added** on assignment detail and task detail pages; API at `/instructions/clusters/{id}` and `/instructions/tasks/{id}`. Instruction Studio global page still levels 1–3 only.
11. **Task memory edit API/UI** — Read-only sidebar today.
12. **RDS sizing** — `db.t3.micro` vs Aurora Serverless v2 (FinOps decision 15) before external launch.
13. **CloudFront default URL** — May still resolve alongside `app.eluven.ai`; disable before external launch?

## CI / ops

14. **Playwright E2E in CI** — Config and login spec exist; not wired into GitHub Actions yet.
15. **GitHub Actions deploy** — Verify `deploy.yml` succeeds with new test suites on next merge to main.
