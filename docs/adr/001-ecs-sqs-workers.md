# ADR 001: Document and workflow workers as dedicated ECS services

**Status:** Accepted  
**Date:** 2026-06-02  
**Context:** MVP audit (June 2026)

## Context

KB document indexing and automated workflow execution depend on SQS queues (`DocumentProcessing`, `WorkflowExecution`). The API enqueues messages on upload or workflow start, but until June 2026 only the **Api** ECS service was deployed. Workers existed in code (`backend/workers/`) but never ran in production, blocking KB → RAG and workflows.

## Decision

Deploy **DocumentWorker** and **WorkflowWorker** as separate `sst.aws.Service` resources in `infra/workers.ts`:

- Same Docker image as the API (`backend/Dockerfile`)
- Different container command: `python -m workers.document_worker` / `python -m workers.workflow_worker`
- No load balancer or service registry (poll-only processes)
- `scaling.min = 1`, `scaling.max = 1` per worker for MVP
- Same VPC, secrets, queue links, and Bedrock permissions as the API

Workers run a **fully async** poll loop (`asyncio.run` + `asyncio.to_thread` for boto3 SQS calls) to avoid SQLAlchemy/asyncpg event-loop conflicts from calling `asyncio.run` per message.

## Consequences

**Positive**

- KB upload → index → RAG path works in production (verified via `scripts/validate_mvp_kb_rag.py`)
- Workflow engine can execute thread steps asynchronously
- Independent scaling and restart of workers vs API (future)

**Negative / trade-offs**

- +2 Fargate tasks at steady state (~$30–40/mo additional vs API-only, depending on CPU/memory)
- Three services share one image; any deploy rebuilds and rolls all three
- Worker logs live in separate CloudWatch log groups under `/sst/cluster/.../DocumentWorker` and `WorkflowWorker`

## Related fixes (same release)

- Plain-text KB files extracted without Unstructured ML deps (`unstructured_inference` not in image)
- `processed_at` stored as naive UTC for PostgreSQL `TIMESTAMP WITHOUT TIME ZONE` compatibility

## Alternatives considered

| Alternative | Why not chosen |
|---|---|
| Run workers in API container (background thread) | Couples API restarts to worker uptime; harder to scale independently |
| Lambda triggered by SQS | Long document processing exceeds Lambda timeout; existing worker code is long-polling |
| Single “Worker” service with supervisord | More complex container; two queues map cleanly to two services |
