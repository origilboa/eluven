#!/usr/bin/env python3
"""Generate eluven_process_and_plan_v1_5.docx from current project state."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.text import WD_BREAK
from docx.shared import Pt

OUTPUT = Path(__file__).resolve().parent.parent / "docs/spec/eluven_process_and_plan_v1_5.docx"


def add_title(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(16)


def add_heading(doc: Document, text: str, level: int = 1) -> None:
    doc.add_heading(text, level=level)


def add_para(doc: Document, text: str, bold: bool = False) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold


def add_bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        doc.add_paragraph(item, style="List Bullet")


def add_table(doc: Document, headers: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    hdr = table.rows[0].cells
    for i, header in enumerate(headers):
        hdr[i].text = header
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = value


def build() -> Document:
    doc = Document()

    add_title(doc, "Eluven")
    add_title(doc, "Academic Research Assistant Platform")
    add_title(doc, "Process & Development Plan")
    add_para(doc, "Version 1.5  |  June 2026")

    add_heading(doc, "Changelog — v1.5 (June 2026)", level=2)
    add_bullets(
        doc,
        [
            "Production deployment complete — internal MVP accessible at https://app.eluven.ai",
            "Foundation build (Weeks 1–2) and substantial portions of Weeks 3–7 implemented in code",
            "End-to-end flow verified in production: login → dashboard → task → thread → AI response (SSE)",
            "Custom domain configured via SST + Route 53 (app.eluven.ai) with ACM certificate",
            "Bedrock model updated from retired Claude 3.5 Sonnet to Claude Sonnet 4.5 inference profile "
            "(us.anthropic.claude-sonnet-4-5-20250929-v1:0)",
            "Production fixes: dev seed on API startup, backend API proxy route handler, tiktoken pre-cache "
            "for no-NAT ECS, Lambda timeout raised to 60s",
            "Frontend UI delivered for dashboard, tasks, threads, KB area, Instruction Studio (minimal MVP UI)",
            "Backend services implemented: AI core, RAG, document pipeline, workflow engine, workers (code complete)",
            "Alembic migrations 001–005 applied in production RDS",
            "Build phase shifts from foundation to validation, gap-fixing, and module completion",
            "Sections 2–7 and 10 unchanged in substance from v1.4 — see v1.4 for full design decision detail",
        ],
    )

    add_para(
        doc,
        "Purpose: This document is the master reference for building Eluven. Load at the start of every "
        "working session alongside the concept document and data model.",
    )
    add_para(
        doc,
        "Concept doc: academic_research_platform_concept_v1_2.docx. "
        "Data model: eluven_data_model_v1_0.docx. "
        "Prior plan version: eluven_process_and_plan_v1_4.docx.",
    )

    add_heading(doc, "1. Project Overview", level=1)
    add_heading(doc, "1.1 What we are building", level=2)
    add_para(
        doc,
        "Eluven is an AI-powered workspace for academic researchers — structured, guided assistance for "
        "reviewing papers, evaluating student submissions, and preparing work for publication. The platform's "
        "core value is structured AI assistance governed by a layered instruction system.",
    )

    add_heading(doc, "1.2 Platform identity", level=2)
    add_table(
        doc,
        ["Item", "Detail"],
        [
            ["Platform name", "Eluven"],
            ["Domain", "eluven.ai"],
            ["Production app URL", "https://app.eluven.ai"],
            ["Registrar", "Namecheap"],
            ["DNS", "AWS Route 53 (hosted zone Z06614832D7DMEV9IQTMN)"],
            ["SSL", "ACM — auto-provisioned by SST for app.eluven.ai"],
            ["Dev credentials (production seed)", "dev@eluven.ai / devpassword123"],
        ],
    )

    add_heading(doc, "1.3 Status at a glance", level=2)
    add_table(
        doc,
        ["Area", "Status"],
        [
            ["Concept & specification", "Complete — concept v1.2, data model v1.0"],
            ["Pre-build decisions", "All resolved (Section 2.1)"],
            ["Pre-external-launch decisions", "Open — Section 2.2 (unchanged from v1.4)"],
            ["Infrastructure", "Production deployed via SST"],
            ["Build status", "Foundation complete; partial Weeks 3–7; validation phase active"],
            ["Current phase", "Test against concept/plan on production; fix gaps; complete modules"],
        ],
    )

    add_heading(doc, "1.4 Completed to date (June 2026)", level=2)
    add_bullets(
        doc,
        [
            "AWS production stack: VPC (no NAT), VPC endpoints, RDS PostgreSQL (db.t3.micro), ECS Fargate API, "
            "S3 documents bucket, SQS queues, Bedrock access, CloudFront + Lambda frontend (OpenNext)",
            "Custom domain app.eluven.ai with Route 53 A/AAAA records and ACM certificate",
            "GitHub repo, Conventional Commits, GitHub Actions (branch / PR / deploy workflows)",
            "Alembic migrations 001–005: full initial schema, EPR + SPR ActivityLibrary seeds, Bedrock model ID updates",
            "Auth: NextAuth.js + FastAPI JWT login; dev user seeded on API container startup",
            "AI core: AIRouter, ContextAssembler, AIClient with Bedrock streaming, task memory writes, RAG retriever",
            "API endpoints: auth, tasks, threads (incl. SSE stream), clusters, KB, instructions, activity library, workflows",
            "Document pipeline (code): Unstructured.io extraction, chunking, embedding, S3 storage, SQS enqueue",
            "Workflow engine (code): sequential execution, intervention triggers, SQS workflow worker",
            "Frontend: Next.js App Router, en/he i18n scaffold, login, dashboard, task detail, thread chat, KB pages, "
            "Instruction Studio page, /api/backend proxy for internal API",
            "Production verification: login, task list/create, thread create, AI streaming response",
        ],
    )

    add_heading(doc, "1.5 Known gaps and deviations (June 2026)", level=2)
    add_bullets(
        doc,
        [
            "Document and workflow SQS workers implemented but not yet deployed as ECS services — uploads may not index",
            "Playwright E2E suite not yet implemented (planned for polish phase)",
            "Hebrew/RTL UI scaffolded but not fully validated in production",
            "Word export, structured Q&A flows, workflow UI, and sample read-only tasks not yet verified end-to-end",
            "Master instructions not yet drafted/tested per thread type (Instruction quality bar from Section 5)",
            "RDS is db.t3.micro single-AZ (FinOps plan referenced Aurora Serverless v2 — revisit before external launch)",
            "04-ai-patterns.mdc and plan still reference Claude 3.5 Sonnet — update to Sonnet 4.5 inference profile",
            "docs/infrastructure/master-reference.md outdated — update in next infrastructure session",
            "CloudFront default URL may still work alongside app.eluven.ai — consider disabling before external launch",
        ],
    )

    add_heading(doc, "1.6 Next sessions in order", level=2)
    add_bullets(
        doc,
        [
            "Production validation — systematic test against concept doc and this plan; file issues per gap",
            "Deploy document + workflow workers to ECS; verify KB upload → index → RAG in thread",
            "External Paper Review module — end-to-end with real PDF, EPR thread types, task memory, Word export",
            "Student Paper Review module — Assignment/Submission UX, batch views, grade output",
            "Workflow engine — UI trigger, status SSE, intervention pause/resume in production",
            "Instruction drafting — master instructions per EPR/SPR thread type; quality testing",
            "Hebrew/RTL validation — layout, locale switch, AI working language",
            "Polish & validate — Playwright E2E (5 critical paths), instruction quality bar, UX friction log",
        ],
    )

    add_heading(doc, "2. Open Decisions", level=1)
    add_para(doc, "Unchanged from v1.4. All pre-build decisions (13–23) remain resolved. Pre-external-launch decisions (5, 9, 11, 16, 24–30) remain open. See v1.4 Section 2 for full detail.", bold=True)

    add_heading(doc, "3. Tech Stack & Infrastructure", level=1)
    add_para(doc, "Application stack unchanged from v1.4 (Next.js, Python/FastAPI, RDS + pgvector, Bedrock, S3, SQS, SST, ECS Fargate). Production-specific updates:", bold=True)
    add_table(
        doc,
        ["Component", "Production detail (June 2026)"],
        [
            ["Frontend URL", "https://app.eluven.ai (CloudFront + Lambda via SST Nextjs)"],
            ["API", "ECS Fargate — internal Cloud Map: Api.production.eluven.sst:8000"],
            ["Database", "RDS PostgreSQL db.t3.micro, private subnet, Alembic on container startup"],
            ["Network", "VPC without NAT; interface endpoints for S3, SQS, Bedrock, Secrets Manager, ECR, Logs, STS"],
            ["AI model (default)", "us.anthropic.claude-sonnet-4-5-20250929-v1:0 (Bedrock inference profile)"],
            ["AI embed model", "amazon.titan-embed-text-v1"],
            ["Secrets", "AWS Secrets Manager via SST (NextAuthSecret, DatabasePassword, AnthropicApiKey)"],
            ["Dev environment", "EC2 t3.xlarge Ubuntu 24 + OrbStack PostgreSQL; Cursor via SSH"],
        ],
    )

    add_heading(doc, "4–7. Development Standards, AI Quality, Design Decisions, Data Model", level=1)
    add_para(doc, "Unchanged from v1.4. Refer to v1.4 Sections 4–7 and eluven_data_model_v1_0.docx.", bold=True)
    add_para(
        doc,
        "Note: Production Alembic history uses migrations 001_initial, 002_activity_library_seed, "
        "003_spr_activity_library_seed, 004_update_bedrock_model_ids, 005_bedrock_inference_profile_ids. "
        "The data model document's migration numbering (001–007 thematic split) was consolidated into fewer files.",
    )

    add_heading(doc, "8. Build Plan", level=1)
    add_para(doc, "MVP scope (8.1, 8.2, 8.3) unchanged from v1.4.", bold=True)

    add_heading(doc, "8.4 Build sequence — progress tracker (updated June 2026)", level=2)
    add_table(
        doc,
        ["Weeks", "Focus", "Status", "Notes"],
        [
            ["1–2", "Foundation", "✓ Complete", "SST deploy, auth, migrations, seed, CI/CD, app.eluven.ai"],
            ["3–4", "Document pipeline + KB", "◐ Partial", "Code complete; worker not on ECS; KB UI exists; needs E2E test"],
            ["4–5", "AI core", "✓ Complete", "Bedrock streaming, context assembly, task memory, RAG — verified in prod"],
            ["6–7", "External Paper Review", "◐ Partial", "ActivityLibrary seeded; thread UI exists; needs full module E2E + instructions"],
            ["8–9", "Student Paper Review", "◐ Partial", "ActivityLibrary seeded; Assignment cluster in seed; needs SPR UX"],
            ["10–11", "Workflow engine", "◐ Partial", "Engine + API + worker code; not deployed/tested in production"],
            ["11–12", "Polish & validate", "○ Not started", "RTL, Instruction Studio quality tools, Playwright E2E, instruction testing"],
        ],
    )
    add_para(doc, "Legend: ✓ Complete  ◐ Partial  ○ Not started")

    add_heading(doc, "8.5 Production validation checklist (current focus)", level=2)
    add_table(
        doc,
        ["#", "Flow", "Status", "URL / notes"],
        [
            ["1", "Login (email/password)", "✓ Verified", "https://app.eluven.ai/en/login"],
            ["2", "Dashboard — list tasks", "✓ Verified", "Seeded + user-created tasks"],
            ["3", "Create task", "✓ Verified", "external_paper_review module"],
            ["4", "Open thread in task", "✓ Verified", ""],
            ["5", "AI response via SSE", "✓ Verified", "Sonnet 4.5 inference profile"],
            ["6", "Upload document to KB collection", "○ To test", "Requires document worker on ECS"],
            ["7", "RAG retrieval in thread", "○ To test", "Depends on #6"],
            ["8", "EPR thread types (initial_read, etc.)", "○ To test", "ActivityLibrary entries exist"],
            ["9", "Task memory display", "○ To test", ""],
            ["10", "Instruction Studio — view/edit versions", "○ To test", "UI + API exist"],
            ["11", "Hebrew locale + RTL layout", "○ To test", "i18n scaffold in place"],
            ["12", "Workflow run + intervention pause", "○ To test", "Worker deployment required"],
            ["13", "Word export", "○ To test", ""],
        ],
    )

    add_heading(doc, "9. Session Protocol", level=1)
    add_heading(doc, "9.1 How to start a session", level=2)
    add_table(
        doc,
        ["Step", "Action"],
        [
            ["1 — Load", "Open eluven_process_and_plan_v1_5.docx, academic_research_platform_concept_v1_2.docx, "
             "and eluven_data_model_v1_0.docx. Use Cursor on EC2 (~/eluven) or reference @docs/spec/ files."],
            ["2 — Test or state goal", "Test on https://app.eluven.ai and report expected vs actual; "
             "or state the build/validation goal for the session."],
            ["3 — Update decisions", "If any Section 2 decisions were resolved, note before starting work."],
            ["4 — End of session", "Update this plan if status changed; commit code; update master-reference.md "
             "if infrastructure changed; add ADR for significant architectural decisions."],
        ],
    )

    add_heading(doc, "9.2 Recommended session types (updated)", level=2)
    add_table(
        doc,
        ["Session type", "When to use", "What to produce"],
        [
            ["Validation session", "NOW — primary mode", "Bug list, gap analysis, fixes deployed to production"],
            ["Worker deployment session", "Before KB/workflow E2E", "ECS services for document + workflow workers"],
            ["Instruction drafting session", "Parallel to EPR/SPR validation", "Master instructions + test results per thread type"],
            ["Module completion session", "Weeks 6–9 gaps", "End-to-end module flows with real documents"],
            ["Polish session", "Before internal user onboarding", "RTL, E2E tests, instruction quality bar"],
            ["Pre-launch sessions", "Before external users", "Decisions 5, 9, 11, 16, 24–30"],
        ],
    )

    add_heading(doc, "10–12. Working Principles, Decision Log, Open Questions", level=1)
    add_para(doc, "Unchanged from v1.4 except for additions below.", bold=True)

    add_heading(doc, "11. Decision Log — additions since v1.4", level=2)
    add_table(
        doc,
        ["Date", "Decision", "Rationale"],
        [
            ["Jun 2026", "Production domain app.eluven.ai via SST domain + Route 53", "User-facing URL on eluven.ai; apex MX preserved"],
            ["Jun 2026", "Backend API proxied via Next.js route handler, not rewrite", "OpenNext breaks rewrites when API URL contains :8000"],
            ["Jun 2026", "Dev seed runs on API container startup", "RDS private; EC2 cannot reach RDS; idempotent seed"],
            ["Jun 2026", "Bedrock Claude Sonnet 4.5 inference profile as default", "Claude 3.5 Sonnet retired on Bedrock; on-demand requires profile ID"],
            ["Jun 2026", "Pre-cache tiktoken + NLTK in Docker image", "ECS tasks have no internet (no NAT); runtime downloads hang"],
            ["Jun 2026", "RDS db.t3.micro instead of Aurora Serverless v2 (initial deploy)", "Simpler first production deploy; revisit for external launch"],
        ],
    )

    add_heading(doc, "13. Document Version History", level=1)
    add_table(
        doc,
        ["Version", "Date", "Summary"],
        [
            ["1.5", "June 2026", "Production deployment status, validation checklist, build progress tracker, "
             "infrastructure as deployed, session protocol update"],
            ["1.4", "May 2026", "Data model complete; build unblocked; foundation next"],
            ["1.3", "May 2026", "Workflow and instruction design decisions resolved"],
            ["1.2", "May 2026", "KB and sharing decisions resolved"],
            ["1.1", "May 2026", "FinOps and infrastructure decisions"],
            ["1.0", "May 2026", "Initial process and plan document"],
        ],
    )

    return doc


def main() -> None:
    doc = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
