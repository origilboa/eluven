# Eluven

AI-powered academic research assistant platform.

## Platform
- **Name:** Eluven
- **Domain:** eluven.ai
- **Stack:** Next.js, Python/FastAPI, AWS Bedrock, PostgreSQL + pgvector, SST on AWS

## Repo structure

| Path | Contents |
|------|----------|
| `/frontend` | Next.js application |
| `/backend` | Python FastAPI application |
| `/infra` | SST infrastructure (AWS CDK) |
| `/docs/adr` | Architecture Decision Records |
| `/docs/spec` | Concept doc, process & plan |
| `/docs/data-model` | Entity schemas, API specifications |
| `/docs/instructions` | Master instruction documents |
| `/docs/infrastructure` | Environment setup, deployment runbooks |
| `/docs/testing` | Test scenarios, Playwright scripts |
| `/scripts` | Seed scripts, utilities |
| `/tests` | Test files mirroring source structure |
| `/.cursor/rules` | Cursor + Claude project rules |

## Development

Development runs on a remote EC2 instance (Ubuntu 24 LTS). Connect via SSH using Cursor.

## Version
1.2 | May 2026
