# MVP internal sign-off plan

**Last updated:** June 2026  
**Production:** https://app.eluven.ai  
**Related:** [open-questions.md](../open-questions.md) · [ADR 002](../adr/002-mvp-scope-decisions-june-2026.md) · [sample-data.md](sample-data.md)

This document defines what “MVP signed off” means, the work required to get there, and how each item is categorized (manual, coding, documentation, testing, ops).

Pre-launch decisions (RDS sizing, billing, security review, external users) are **out of scope** for this sign-off.

---

## Sign-off definition

MVP is signed off when **all** of the following are true:

| # | Criterion | Work type |
|---|-----------|-----------|
| A | One EPR task completed on a real text-layer PDF; output quality accepted | Manual · Documentation |
| B | One SPR Assignment → Submission → review path completed; output accepted | Manual · Documentation |
| C | KB → index → RAG in thread verified on a Task with an attached collection | Manual · Testing |
| D | Automated validation green: txt, pdf, docx indexing + backend unit tests | Testing |
| E | Platform instructions exist for all 11 EPR/SPR thread types (quality-tested) | Coding · Documentation · Manual |
| F | UX friction log completed from internal runs | Documentation |
| G | Hebrew/RTL smoke pass documented | Manual · Testing · Documentation |
| H | Remaining MVP-spec technical gaps either **fixed** or **explicitly waived in writing** | Coding or Documentation |

**Sign-off artifact:** `docs/validation/mvp-signoff-YYYY-MM-DD.md` (see Phase 5).

---

## Current baseline (June 2026)

Already in place:

- Production stack: Api, DocumentWorker, WorkflowWorker on ECS
- Auth, Tasks, Threads, AI SSE, KB indexing (txt / pdf / docx validated on prod)
- EPR + SPR modules, Assignment/Submission hierarchy, workflows UI, module-aware Word export
- Instruction Studio (levels 1–3: platform / org / user)
- ADR 002 decisions: lightweight extractors, minimal SPR, generic Word export

Not yet done:

- Human validation runs (EPR, SPR, workflow, RAG, RTL)
- Platform instructions for 9 of 11 thread types
- Several spec items (rate limits, thread doc upload UI, choice-type Q&A, memory edit)
- Playwright in CI; deploy.yml not verified green after recent changes

---

## Phase 1 — Run the product (blocking)

Do this first. Later phases depend on what you find.

### 1.1 EPR validation run

| | |
|---|---|
| **Type** | Manual · Documentation |
| **Blocks** | Criterion A |

**Steps:**

1. Log in at https://app.eluven.ai (`dev@eluven.ai` / dev credentials)
2. Create an EPR Task; upload a **real text-layer PDF** (not a scan)
3. Attach a KB collection with 1–2 reference documents
4. Run threads in order: `initial_read` → … → `final_recommendation`, **or** start the “EPR Full Review” workflow
5. Confirm TaskMemory populates during chat
6. Export Word; open the file and review structure
7. Log every friction point (confusing UI, bad AI output, broken flow)

**Artifact:** `docs/validation/mvp-epr-run-YYYY-MM-DD.md`

**Template sections:** setup · thread-by-thread notes · memory quality · Word export · RAG (yes/no) · workflow (yes/no) · blockers · waivers

---

### 1.2 SPR validation run

| | |
|---|---|
| **Type** | Manual · Documentation |
| **Blocks** | Criterion B |

**Steps:**

1. Create an Assignment cluster
2. Add a Submission under it
3. Run SPR threads on the submission (`submission_read` → … → `grade_recommendation`)
4. Confirm hierarchy in UI (Assignments list → cluster detail → submission task)
5. Export Word for the submission
6. Log friction

**Artifact:** `docs/validation/mvp-spr-run-YYYY-MM-DD.md`

---

### 1.3 RAG-in-thread check

| | |
|---|---|
| **Type** | Manual · Testing |
| **Blocks** | Criterion C |

**Steps:**

1. During an EPR thread, ask a question answerable **only** from the attached KB
2. Confirm the answer uses KB content (not hallucinated)
3. Note if citations/source attribution are missing (acceptable for MVP if retrieval works)

**Artifact:** one line in the EPR validation doc: `RAG verified: yes/no` + brief note

---

### 1.4 Workflow + intervention check

| | |
|---|---|
| **Type** | Manual · Testing |
| **Blocks** | Part of Criterion A |

**Steps:**

1. Start “EPR Full Review” workflow on a task
2. Let it run until completion or intervention pause
3. If paused, respond via the workflow panel and confirm resume
4. Log any worker/SQS issues

**Artifact:** workflow status noted in EPR validation doc

---

### 1.5 Hebrew/RTL smoke pass

| | |
|---|---|
| **Type** | Manual · Testing · Documentation |
| **Blocks** | Criterion G |

**Steps:**

1. Switch locale to `he` (URL or UI)
2. Walk: login → dashboard → create task → thread chat → KB → Instruction Studio
3. Check: text alignment, nav order, form labels, no broken layouts
4. Log RTL-specific issues only (do not re-test all English flows)

**Artifact:** `docs/validation/mvp-rtl-pass-YYYY-MM-DD.md`

---

### 1.6 UX friction log

| | |
|---|---|
| **Type** | Documentation |
| **Blocks** | Criterion F |

Consolidate friction from 1.1–1.5 into one table.

**Template:**

| # | Area | What happened | Severity (blocker / annoyance / nice) | Fix now or defer? |
|---|------|---------------|---------------------------------------|-------------------|

**Artifact:** `docs/validation/mvp-friction-log.md` (or section inside each run doc)

---

## Phase 2 — Content (blocks quality sign-off)

Instructions are core product IP. Two seeded thread types is not enough for credible EPR/SPR runs.

### 2.1 Platform instructions for remaining thread types

| | |
|---|---|
| **Type** | Documentation · Coding · Manual |
| **Blocks** | Criterion E |

**Already seeded (migration 006):**

- `initial_read`
- `final_recommendation`

**EPR — still needed (4):**

- `methodology_review`
- `literature_review`
- `results_analysis`
- `writing_quality`

**SPR — still needed (5):**

- `submission_read`
- `rubric_evaluation`
- `feedback_generation`
- `grade_recommendation`
- `version_comparison`

**Per thread type:**

1. Draft instruction content (Instruction Studio as app_admin, or direct migration)
2. Test in a real thread; iterate until output is usable
3. Publish as active platform-level instruction version

**Delivery options:**

- **Preferred for MVP:** migration `007_platform_instruction_seeds.py` for reproducibility across environments
- **Alternative:** create via Instruction Studio in production, then export/backfill to migration

**Artifact:** all 11 types have active platform instructions; quality notes in validation docs

---

## Phase 3 — Fix blockers from Phase 1

Triage the friction log: **blockers must be fixed** before sign-off. Annoyances may be deferred with a written waiver in `docs/open-questions.md`.

### 3.1 Likely coding work (prioritize by Phase 1 findings)

| Item | Type | MVP blocker? | Notes |
|------|------|--------------|-------|
| Thread document upload UI | Coding | If runs need per-thread docs | Backend exists; no frontend |
| Choice-type Q&A UI (`single_select`, `multi_select`) | Coding | If opening questions block flows | UI only renders textareas today |
| Task memory edit API + UI | Coding | If reviewers must correct memory | Read-only sidebar; GET-only API |
| Rate limiting (10 AI calls/min) | Coding | Recommended before multi-user internal use | Spec §4; not implemented |
| Workflow concurrency cap (3/user) | Coding | Recommended before multi-user internal use | Not enforced |
| Read-only sample tasks on dashboard empty state | Coding | No | Creates editable tasks today; demo nice-to-have |

**Sign-off rule:** each deferred item gets one line in `docs/open-questions.md`:

> Waived for MVP sign-off because …

---

### 3.2 Instruction Studio levels 4–5 (cluster / task / thread)

| | |
|---|---|
| **Type** | Coding |
| **Recommendation** | **Defer** unless Phase 1 shows cluster-level instructions are required for SPR |

Platform/org/user instructions + per-thread-type platform seeds are sufficient for internal validation.

If deferred, document waiver in open-questions.

---

## Phase 4 — Automated testing & CI

### 4.1 Run validation scripts

| | |
|---|---|
| **Type** | Testing · Ops |
| **Blocks** | Criterion D |

```bash
# From repo root
python3 scripts/run_mvp_validation.py

# Backend unit tests
cd backend && poetry run pytest

# Frontend unit tests
cd frontend && pnpm test
```

**Sign-off:** all green before formal sign-off.

---

### 4.2 Optional extensions

| Item | Type | Priority |
|------|------|----------|
| Add `--fixture xlsx` / `--fixture csv` to `validate_mvp_kb_rag.py` | Coding · Testing | Low — only if KB uses spreadsheets |
| Playwright smoke: login → create task → open thread | Coding · Testing | Medium |
| Wire Playwright into GitHub Actions | Ops · Testing | Medium |

Minimum for sign-off: backend pytest + `run_mvp_validation.py` green. Playwright in CI may be waived with documentation.

---

### 4.3 CI / deploy verification

| | |
|---|---|
| **Type** | Testing · Ops |

1. Push to `main`; confirm `.github/workflows/deploy.yml` succeeds
2. Ensure deploy uses `CI=true` for frontend/OpenNext build (pnpm non-TTY issue on EC2)
3. Consider adding frontend test step to deploy workflow

**Artifact:** link to green CI run on the sign-off commit

---

## Phase 5 — Documentation & formal close

### 5.1 Update living docs

| Document | Action | Type |
|----------|--------|------|
| `docs/open-questions.md` | Close resolved items; add waivers | Documentation |
| `docs/infrastructure/master-reference.md` | Validation status, ADR 002, deploy note (`CI=true`) | Documentation |
| `scripts/generate_plan_v1_6.py` → plan v1.6 docx | Regenerate with sign-off checklist status | Documentation |
| `docs/validation/` | Add EPR, SPR, RTL, friction log, sign-off record | Documentation |

---

### 5.2 Sign-off decision record

| | |
|---|---|
| **Type** | Documentation |

Create `docs/validation/mvp-signoff-YYYY-MM-DD.md`:

```markdown
## MVP internal sign-off — [date]

**Decision:** Signed off / Not signed off

**Evidence:**
- EPR run: [link to mvp-epr-run doc]
- SPR run: [link to mvp-spr-run doc]
- RTL pass: [link]
- Automated checks: [CI link / script output]
- Instructions: 11/11 platform thread types (or list gaps)

**Known waivers (accepted for internal MVP):**
- [item] — because [reason]

**Not in scope (pre-launch):**
- RDS sizing, CloudFront default URL, billing, security review, external users, …
```

---

## Work-type summary

| Type | Items | Rough effort |
|------|-------|--------------|
| **Manual** | EPR run, SPR run, RAG check, workflow run, Hebrew pass | 1–2 days |
| **Documentation** | Friction log, validation write-ups, instructions, sign-off record, doc updates | 2–3 days (overlaps manual) |
| **Coding** | Instruction seeds (007), blockers from friction log, rate limits, optional UI gaps | 2–5 days (depends on Phase 1) |
| **Testing** | `run_mvp_validation.py`, pytest, optional Playwright, CI green | 0.5–1 day |
| **Ops** | Deploy fixes, `CI=true` in deploy.yml, verify GitHub Actions | 0.5 day |

**Critical path:** Phase 1 → Phase 2 → Phase 3 (blockers only) → Phase 4 → Phase 5

---

## Minimal path (fast sign-off)

If time is constrained, smallest credible internal sign-off:

1. **Manual:** EPR + SPR runs + friction log (Phase 1.1, 1.2, 1.6)
2. **Documentation:** Instructions for thread types actually used in those runs (document any gaps)
3. **Testing:** `run_mvp_validation.py` + pytest green
4. **Documentation:** Sign-off doc with explicit waivers for rate limits, Instruction Studio 4–5, read-only sample tasks, Playwright CI

This yields **“internal MVP validated with known gaps”** — honest for solo internal use, not external launch.

---

## Explicitly out of scope (ADR 002 + pre-launch)

Do not block MVP sign-off on these:

| Item | Reason |
|------|--------|
| Batch SPR grading dashboard, grade book, class report | ADR 002 — minimal SPR |
| Publisher-grade Word report templates | ADR 002 — generic export |
| OCR / scanned PDF indexing | ADR 002 — text-layer PDFs only |
| Unstructured ML extraction pipeline | ADR 002 |
| RDS sizing, Aurora decision | Pre-launch FinOps |
| CloudFront default URL disable | Pre-launch |
| Pricing, billing, legal, security review | Pre-launch §2.2 |

---

## Checklist (copy for tracking)

Use this as a living checklist; check items off as completed.

### Phase 1 — Manual validation

- [ ] 1.1 EPR validation run documented
- [ ] 1.2 SPR validation run documented
- [ ] 1.3 RAG-in-thread verified
- [ ] 1.4 Workflow + intervention verified
- [ ] 1.5 Hebrew/RTL smoke pass documented
- [ ] 1.6 UX friction log consolidated

### Phase 2 — Instructions

- [ ] `methodology_review` platform instruction
- [ ] `literature_review` platform instruction
- [ ] `results_analysis` platform instruction
- [ ] `writing_quality` platform instruction
- [ ] `submission_read` platform instruction
- [ ] `rubric_evaluation` platform instruction
- [ ] `feedback_generation` platform instruction
- [ ] `grade_recommendation` platform instruction
- [ ] `version_comparison` platform instruction

### Phase 3 — Code (as needed from friction log)

- [ ] Blocker fixes implemented
- [ ] Waivers documented for deferred items

### Phase 4 — Automated

- [ ] `run_mvp_validation.py` passes
- [ ] `poetry run pytest` passes
- [ ] `pnpm test` passes
- [ ] CI deploy green on sign-off commit

### Phase 5 — Close

- [ ] `docs/open-questions.md` updated
- [ ] `docs/infrastructure/master-reference.md` updated
- [ ] `docs/validation/mvp-signoff-YYYY-MM-DD.md` created
- [ ] Plan v1.6 regenerated (optional)
