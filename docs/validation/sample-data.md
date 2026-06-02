# Demo sample data for MVP testing

Rich, idempotent dataset for manual validation. Safe to re-run — existing entities are skipped by title/email.

## How to load

**Full reset** (recommended — restores migration seeds + all demo data):

```bash
cd backend
poetry run python ../scripts/seed.py --reset-demo
```

Incremental loads:

```bash
cd backend
poetry run python ../scripts/seed.py --demo
poetry run python ../scripts/seed.py --instructions   # cluster/task instructions only
```

`--reset-demo` runs `alembic downgrade 001 && alembic upgrade head` then `--demo`.  
This restores ActivityLibrary, platform instructions, workflow templates, and all demo entities
(instruction levels org/user/cluster/task/thread addenda, all TaskMemory entry types, KB, workflows).

Or from EC2 with production credentials (one-time, when you want demo tasks in prod):

```bash
cd /home/ubuntu/eluven/backend
poetry run python ../scripts/seed.py --reset-demo
```

Minimal startup seed (API container) remains `--dev` only:

```bash
python scripts/seed.py --dev
```

## Users

Both users belong to **Dev Org** (`dev-org`).

| Email | Password | Role | Purpose |
|-------|----------|------|---------|
| `dev@eluven.ai` | `devpassword123` | app_admin | Full access, Instruction Studio platform tab |
| `reviewer@eluven.ai` | `reviewpassword123` | user | Second account — separate task list |

## Demo tasks (prefix `Demo `)

All demo tasks are titled with the **`Demo `** prefix so they are easy to find and distinguish from real work.

### External Paper Review (dev@eluven.ai)

| Task | Status | Contents |
|------|--------|----------|
| Demo EPR — Draft (empty) | draft | Empty shell for upload / first-thread flows |
| Demo EPR — Methods paper (in progress) | active | 2 threads, 5 memory entries, KB attached |
| Demo EPR — Hebrew locale | active | `working_language=he` for RTL pass |
| Demo EPR — Workflow paused (intervention) | active | Paused workflow with pending intervention |

### External Paper Review (reviewer@eluven.ai)

| Task | Status |
|------|--------|
| Demo EPR — Reviewer-owned journal paper | active |

### Student Paper Review (dev@eluven.ai)

| Entity | Details |
|--------|---------|
| **Assignment** | Demo Assignment — Research Methods 101 |
| **Submission (active)** | Demo SPR — Alice Chen submission — thread + memory |
| **Submission (draft)** | Demo SPR — Bob Martinez submission — empty draft |

## Threads and memory

**Demo EPR — Methods paper (in progress):**

- `initial_read` — complete, sample conversation
- `methodology_review` — active, sample conversation
- TaskMemory: 2 findings, 1 assumption, 1 gap, 1 reference

**Demo SPR — Alice Chen submission:**

- `submission_read` — active, sample conversation
- TaskMemory: 1 finding

## Knowledge base

| Collection | Attached to | Notes |
|------------|-------------|-------|
| Demo Reference — methodology guides | Methods paper (in progress) task | `methods-guide.txt` marked READY with 2 chunks |

**RAG note:** Demo chunks use zero embeddings for seed simplicity. They appear in the KB UI as indexed documents. For live RAG retrieval testing, upload real files through the UI or run the validation script.

## Workflow demo

**Demo EPR — Workflow paused (intervention):**

- Status: `paused` on step 2 (`methodology_review`)
- Intervention question: competing definitions of “engagement”
- Use the workflow panel to respond and test resume (may require worker for full automation)

## Cluster and task instructions (UI)

After loading demo data, edit instructions in the app:

| Location | What to set |
|----------|-------------|
| **Assignment detail** (`/clusters/{id}`) | Cluster-level instructions for all submissions — e.g. rubric notes for `Demo Assignment — Research Methods 101` |
| **Task detail** (`/tasks/{id}`) | Task-level instructions (versioned) + per-thread-type addendum |

Use **Thread scope** to apply instructions to all thread types or one ActivityLibrary thread type. Instructions are merged into AI context at levels 4–5 automatically.

**Seeded sample content** (via `--instructions`):

| Target | Content |
|--------|---------|
| Demo Assignment cluster | Class rubric (all threads) + rubric_evaluation-specific scoring guide |
| Demo EPR — Methods paper | Review priorities + `initial_read` thread addendum |
| Demo SPR — Alice Chen | Feedback tone + `submission_read` addendum |
| Sample Paper Review | Generic EPR test instructions |

## Clearing demo data

```bash
poetry run python ../scripts/seed.py --clear
poetry run python ../scripts/seed.py --dev    # restore minimal dev user
poetry run python ../scripts/seed.py --demo   # reload full demo set
```

`--clear` truncates all application tables except platform org and Alembic version.

## Related

- [MVP sign-off plan](mvp-signoff-plan.md)
- [open-questions.md](../open-questions.md)
