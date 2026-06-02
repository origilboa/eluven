# Eluven Infrastructure Master Reference

Last updated: June 2, 2026

> This document is the single source of truth for all infrastructure,
> accounts, services, and configurations. Update after every session.

---

## Domain & DNS

| Item | Detail |
|---|---|
| Domain | eluven.ai |
| Registrar | Namecheap |
| Nameservers | Delegated to Route 53 (AWS) |
| DNS provider | AWS Route 53 |
| Hosted zone ID | Z06614832D7DMEV9IQTMN |
| Production app URL | https://app.eluven.ai |
| SSL certificate | ACM — arn:aws:acm:us-east-1:124871951150:certificate/e479bebb-cdd6-4909-a2c5-8039ed3c2241 |
| SSL covers | eluven.ai + *.eluven.ai |
| SSL status | Issued |
| Privacy protection | WhoisGuard via Namecheap — enabled |

### DNS Records in Route 53
| Type | Name | Value | Purpose |
|---|---|---|---|
| NS | eluven.ai | 4 AWS nameservers | Domain delegation |
| MX | eluven.ai | Google Workspace MX records | Email routing |
| A / AAAA | app.eluven.ai | CloudFront distribution | Production frontend |
| CNAME | _b568720054dfad612de09608c51d9d89.eluven.ai | ACM validation record | SSL validation |

---

## Email

| Item | Detail |
|---|---|
| Provider | Google Workspace |
| Primary account | ori.gilboa@eluven.ai |
| Role | Platform admin, all Eluven communications |
| Recovery email | Personal Gmail (origilboa@gmail.com) |

---

## AWS Account

| Item | Detail |
|---|---|
| Account name | eluven |
| Account ID | 124871951150 |
| Root email | origilboa@gmail.com |
| Root MFA | Enabled (authenticator app) |
| Root access keys | None (correct — never create) |
| Plan | Standard pay-as-you-go |
| Free credits | $100 USD, expires Nov 30, 2026 |
| Primary region | us-east-1 |

### IAM Users
| User | Purpose | Permissions |
|---|---|---|
| eluven-dev | Daily CLI and development use | AdministratorAccess |

### IAM Roles
| Role | Purpose | ARN |
|---|---|---|
| eluven-github-deploy | GitHub Actions CI/CD deployments | arn:aws:iam::124871951150:role/eluven-github-deploy |

### Cost Controls
| Budget | Threshold | Alert email |
|---|---|---|
| Eluven Monthly Total | $50 | ori.gilboa@eluven.ai |
| Eluven Bedrock Monthly Budget | $30 | ori.gilboa@eluven.ai |
| Eluven Infrastructure Monthly Budget | $20 | ori.gilboa@eluven.ai |
| Anomaly Monitor | $20 spike | ori.gilboa@eluven.ai |

---

## EC2 Dev Server

| Item | Detail |
|---|---|
| Instance ID | i-02e28fbb277628ada |
| Instance type | t3.xlarge (4 vCPU, 16GB RAM) |
| AMI | Ubuntu 24.04 LTS |
| Region | us-east-1 |
| Storage | 50GB gp3 |
| Security group | sg-014bad2a06964d191 (SSH port 22) |
| Key pair | eluven-dev |
| SSH key location (Mac) | ~/.ssh/eluven-dev |
| SSH host alias | eluven-dev (in ~/.ssh/config) |
| Public IP | Dynamic — changes on stop/start; `eluven-start` handles this |
| OS user | ubuntu |
| Cost | ~$0.17/hr when running |

### Installed on EC2
| Tool | Version | Purpose |
|---|---|---|
| Ubuntu | 24.04 LTS | Operating system |
| Python | 3.12 | Backend runtime |
| Node.js | 20 | Frontend + SST |
| Poetry | 2.4.1 | Python dependency management |
| pnpm | 10.x (global via npm) | JS dependency management |
| Docker | latest | Container runtime (OrbStack) |
| AWS CLI | v2 | AWS access |
| Git | system | Source control |

### Running containers on EC2 (local dev)
| Container | Image | Port | Purpose |
|---|---|---|---|
| eluven-postgres | pgvector/pgvector:pg16 | 5432 | Local PostgreSQL + pgvector |

### EC2 environment variables (~/.bashrc)
| Variable | Value |
|---|---|
| DATABASE_URL | postgresql://eluven:eluven_dev_password@localhost:5432/eluven |

### Mac shell aliases (`~/.zshrc`)
| Command | What it does |
|---|---|
| `eluven-start` | Start EC2, RDS, ECS; update SSH config; connect |
| `eluven-stop` | Scale ECS to 0, stop RDS, stop EC2 |
| `eluven-status` | Show EC2, ECS, RDS state |
| `eluven-check` | Pre-stop safety check |

Scripts: `scripts/infra/` — see [README.md](../../scripts/infra/README.md)

---

## Database

### Local dev (EC2 / OrbStack)
| Item | Detail |
|---|---|
| Engine | PostgreSQL 16 + pgvector |
| Host | localhost |
| Port | 5432 |
| Database name | eluven |
| Username | eluven |
| Password | eluven_dev_password |
| Migrations | Alembic — apply with `poetry run alembic upgrade head` |

### Production (RDS)
| Item | Detail |
|---|---|
| Engine | PostgreSQL 16 (RDS) |
| Instance | db.t3.micro |
| Identifier | eluven-production-databaseinstance-vmdmnvvm |
| Network | Private subnet in VPC (no public access) |
| Credentials | AWS Secrets Manager — `DatabasePassword` via SST |
| Migrations | Alembic `upgrade head` on API container startup |
| Applied migrations | 001–006 (006 adds workflow templates + platform instruction seeds) |
| pgvector | Enabled in migration 001 |

---

## AWS Secrets Manager (production)

| Secret (SST name) | Purpose | Status |
|---|---|---|
| AnthropicApiKey | Bedrock / Anthropic API key | Set |
| DatabasePassword | RDS production password | Set |
| NextAuthSecret | NextAuth.js session secret | Set |

---

## SST Production Stack (deployed)

Deploy from EC2: `npx sst deploy --stage production`

| Resource | SST component | File | Notes |
|---|---|---|---|
| VPC | sst.aws.Vpc | infra/database.ts | No NAT gateway |
| VPC endpoints | aws.ec2.VpcEndpoint | infra/vpc-endpoints.ts | S3, SQS, Bedrock, Secrets Manager, ECR, Logs, STS |
| RDS PostgreSQL | sst.aws.Postgres | infra/database.ts | db.t3.micro |
| S3 documents | sst.aws.Bucket | infra/storage.ts | Versioning enabled |
| SQS DocumentProcessing | sst.aws.Queue | infra/queues.ts | 300s visibility |
| SQS WorkflowExecution | sst.aws.Queue | infra/queues.ts | 600s visibility |
| ECS cluster | sst.aws.Cluster | infra/api.ts | EluvenCluster |
| **Api** | sst.aws.Service | infra/api.ts | FastAPI, port 8000, Cloud Map |
| **DocumentWorker** | sst.aws.Service | infra/workers.ts | SQS poll, document indexing |
| **WorkflowWorker** | sst.aws.Service | infra/workers.ts | SQS poll, workflow steps |
| Frontend | sst.aws.Nextjs | infra/frontend.ts | OpenNext → CloudFront |
| Secrets | sst.Secret | infra/secrets.ts | Linked to services |

### ECS services (cluster `eluven-production-EluvenClusterCluster-bcxhvdvx`)

| Service | Desired count | Cloud Map / URL |
|---|---|---|
| Api | 1 | Api.production.eluven.sst:8000 (internal) |
| DocumentWorker | 1 | DocumentWorker.production.eluven.sst |
| WorkflowWorker | 1 | WorkflowWorker.production.eluven.sst |

### CloudWatch log groups
| Service | Log group pattern |
|---|---|
| Api | `/sst/cluster/.../Api` |
| DocumentWorker | `/sst/cluster/.../DocumentWorker` |
| WorkflowWorker | `/sst/cluster/.../WorkflowWorker` |
| Frontend Lambda | `/aws/lambda/eluven-production-Frontend*` |

### AI models (production)
| Use | Model ID |
|---|---|
| Chat (default) | us.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| Embeddings | amazon.titan-embed-text-v1 |

### Dev seed (production API startup)
- `alembic upgrade head && python /app/scripts/seed.py --dev && uvicorn ...`
- Dev user: dev@eluven.ai / devpassword123

---

## GitHub

| Item | Detail |
|---|---|
| Account | origilboa (personal account) |
| Repo | https://github.com/origilboa/eluven (private) |
| Default branch | main |
| Branching strategy | Feature branches → PR → merge to main |

### GitHub Actions
| Workflow | Trigger | Checks |
|---|---|---|
| branch.yml | Push to non-main branches | Ruff, Pyright, pytest unit, ESLint, tsc, Jest |
| pr.yml | PR to main | Above + integration tests |
| deploy.yml | Push to main | Deploy via SST |

### GitHub Actions secrets
| Secret | Purpose |
|---|---|
| AWS_DEPLOY_ROLE_ARN | arn:aws:iam::124871951150:role/eluven-github-deploy |

---

## Mac Development Environment

| Item | Detail |
|---|---|
| Machine | MacBook Air |
| Shell | zsh — aliases in **~/.zshrc** (not .zprofile) |
| AWS CLI | v2 — eluven-dev credentials |
| Node.js | 26 (Homebrew) |
| SSH key | ~/.ssh/eluven-dev |

---

## Validation scripts

| Script | Purpose |
|---|---|
| `scripts/validate_mvp_kb_rag.py` | Upload KB doc, poll until `ready` |
| `scripts/run_mvp_validation.py` | Run automated MVP checklist |

---

## Architecture decision records

| ADR | Title |
|---|---|
| [001-ecs-sqs-workers.md](../adr/001-ecs-sqs-workers.md) | Document and workflow workers as dedicated ECS services |

---

## Next steps (June 2026)

1. Internal validation — one full EPR task + one full SPR task; log UX friction (`docs/open-questions.md`)
2. PDF indexing path — decide Unstructured ML deps vs alternative for production Docker image
3. Instruction drafting — remaining EPR/SPR thread types
4. Wire Playwright E2E into CI
5. Pre-launch decisions (Section 2.2 of process plan) before external users
