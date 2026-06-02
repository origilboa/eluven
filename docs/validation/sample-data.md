# Demo sample data for MVP testing

Rich, idempotent dataset for manual validation. Safe to re-run on an existing DB — existing entities are skipped by title/email.

## How to load

**Full reset** (recommended — wipes DB, restores migration seeds, loads demo):

```bash
cd backend
poetry run python ../scripts/seed.py --reset-demo
```

`--reset-demo` runs `alembic downgrade 001`, `alembic upgrade head`, then `--demo`.  
This deletes all prior application data (except platform org), re-seeds ActivityLibrary, workflow templates, platform instructions, and the full demo dataset.

**Do not** use `--clear` followed by `--demo` — `--clear` removes migration seeds and `--demo` does not restore them.

Incremental reload (keeps non-demo data created manually):

```bash
cd backend
poetry run python ../scripts/seed.py --demo
poetry run python ../scripts/seed.py --instructions   # cluster/task instructions only
```

### AWS and offline seed

Document seeding uploads fixtures to S3 and runs the document processor (real embeddings for KB). Requires dev AWS credentials (S3 + Bedrock), same as SST dev.

```bash
SEED_SKIP_AWS=1 poetry run python ../scripts/seed.py --demo
```

Skips S3 upload/processing; DB rows may stay `pending` — use only when AWS is unavailable.

Minimal API container startup remains `--dev` only (not demo):

```bash
python scripts/seed.py --dev
```

## Users (Dev Org `dev-org`)

| Email | Password | Role | Purpose |
|-------|----------|------|---------|
| `dev@eluven.ai` | `devpassword123` | app_admin | Environment admin — Instruction Studio platform tab, org list |
| `orgadmin@eluven.ai` | `orgadminpassword123` | org_admin | Org admin — users + invitations (no platform org tab) |
| `reviewer@eluven.ai` | `reviewpassword123` | user | Standard researcher — separate task list |

**Second org (empty):** `demo-org-b` — for app_admin organization list smoke tests.

**Pending invitation:** `invitee@eluven.ai` (not yet a user). Accept-invite token (dev only):

`/en/accept-invite?token=demo-invite-token-for-mvp-testing-only`

## After reset — feature map

| Feature | Where to test |
|---------|----------------|
| EPR task + threads + memory | **Demo EPR — Methods paper (in progress)** |
| Paper under review (PDF) | Same task — `demo-manuscript.pdf` |
| KB + RAG | Same task — collection **Demo Reference — methodology guides** |
| Cluster KB attach | **Demo Assignment — Research Methods 101** |
| Opening Q&A | Methods task → **Initial Read** thread → Q&A |
| Paused EPR workflow | **Demo EPR — Workflow paused (intervention)** |
| Paused SPR workflow | **Demo SPR — Workflow paused (intervention)** |
| SPR submission | **Demo SPR — Alice Chen submission** |
| RTL | **Demo EPR — Hebrew locale** |
| Per-user tasks | Log in as `reviewer@` |
| Admin users / invites | Log in as `orgadmin@` or `dev@` → Admin |
| Org list (app_admin) | Log in as `dev@` → Admin → Organizations |

## Demo tasks (prefix `Demo `)

### External Paper Review (`dev@eluven.ai`)

| Task | Status | Contents |
|------|--------|----------|
| Demo EPR — Draft (empty) | draft | Empty shell |
| Demo EPR — Methods paper (in progress) | active | Threads, memory, KB, paper PDF, Q&A sample |
| Demo EPR — Hebrew locale | active | `working_language=he` |
| Demo EPR — Workflow paused (intervention) | active | Paused EPR workflow |

### External Paper Review (`reviewer@eluven.ai`)

| Task | Status |
|------|--------|
| Demo EPR — Reviewer-owned journal paper | active |

### Student Paper Review (`dev@eluven.ai`)

| Entity | Details |
|--------|---------|
| **Assignment** | Demo Assignment — Research Methods 101 |
| **Submission (active)** | Demo SPR — Alice Chen — thread, memory, paper PDF |
| **Submission (draft)** | Demo SPR — Bob Martinez — empty draft |
| **Workflow demo** | Demo SPR — Workflow paused (intervention) |

## Knowledge base

| Collection | Attached to | Document |
|------------|-------------|----------|
| Demo Reference — methodology guides | Methods EPR task + Demo Assignment cluster | `methods-guide.txt` (processed via document pipeline when AWS available) |

## Workflow demos

| Task | Template | Notes |
|------|----------|-------|
| Demo EPR — Workflow paused | EPR Full Review | Paused on step 2; engagement definition question |
| Demo SPR — Workflow paused | SPR Full Evaluation | Paused on step 2; rubric vs citation date question |

Workflow **resume** after intervention requires WorkflowWorker running.

## Cluster and task instructions

Seeded with `--demo` (org, user, cluster, task, thread addenda). Edit in app on assignment/task detail or Instruction Studio (levels 1–3 as `dev@`).

## Related

- [MVP sign-off plan](mvp-signoff-plan.md)
- [open-questions.md](../open-questions.md)
