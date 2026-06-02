# Open questions — post MVP audit (June 2026)

Tracked after MVP completeness implementation. Resolve before external launch or next major milestone.

## Product / validation

1. **EPR end-to-end with real PDF** — ActivityLibrary, Word export, and workflow UI exist; has a reviewer completed one full paper review task and signed off on output quality?
2. **SPR end-to-end** — Assignment/submission UI and API exist; batch grading views and grade output format still minimal per concept doc.
3. **Master instruction quality** — Only `initial_read` and `final_recommendation` platform seeds in migration 006; remaining EPR/SPR thread types need drafted instructions and quality testing.
4. **Hebrew/RTL production validation** — i18n scaffold and logical CSS in place; full UI pass in `he` locale not documented.
5. **UX friction log** — MVP success criterion §8.3; no structured friction notes yet from internal users.

## Technical

6. **PDF/DOCX indexing in production** — Plain `.txt` validated; Unstructured ML stack not in Docker image (`unstructured_inference` omitted). Need decision: add deps vs lighter extractors for MVP PDF path.
7. **Rate limiting (10 AI calls/min)** — Spec §4; not implemented.
8. **Concurrent workflow limit (3/user)** — Not enforced.
9. **Thread document upload UI** — Backend upload exists; no frontend.
10. **Instruction Studio levels 4–5** — Cluster/task/thread instruction APIs partial; UI shows platform/org/user only.
11. **Task memory edit API/UI** — Read-only sidebar today.
12. **RDS sizing** — `db.t3.micro` vs Aurora Serverless v2 (FinOps decision 15) before external launch.
13. **CloudFront default URL** — May still resolve alongside `app.eluven.ai`; disable before external launch?

## CI / ops

14. **Playwright E2E in CI** — Config and login spec exist; not wired into GitHub Actions yet.
15. **GitHub Actions deploy** — Verify `deploy.yml` succeeds with new test suites on next merge to main.
