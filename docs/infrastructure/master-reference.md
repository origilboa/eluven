# Eluven Infrastructure Master Reference

Last updated: May 31, 2026

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
| SSL certificate | ACM — arn:aws:acm:us-east-1:124871951150:certificate/e479bebb-cdd6-4909-a2c5-8039ed3c2241 |
| SSL covers | eluven.ai + *.eluven.ai |
| SSL status | Issued |
| Privacy protection | WhoisGuard via Namecheap — enabled |

### DNS Records in Route 53
| Type | Name | Value | Purpose |
|---|---|---|---|
| NS | eluven.ai | 4 AWS nameservers | Domain delegation |
| MX | eluven.ai | Google Workspace MX records | Email routing |
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
| AMI | Ubuntu 24.04 LTS (ami-067bcf851477ebb78) |
| Region | us-east-1 |
| Storage | 50GB gp3 |
| Security group | sg-014bad2a06964d191 (SSH port 22) |
| Key pair | eluven-dev |
| SSH key location (Mac) | ~/.ssh/eluven-dev |
| SSH host alias | eluven-dev (in ~/.ssh/config) |
| Public IP | Dynamic — changes on stop/start, eluven-start handles this |
| OS user | ubuntu |
| Cost | ~$0.17/hr when running |

### Installed on EC2
| Tool | Version | Purpose |
|---|---|---|
| Ubuntu | 24.04 LTS | Operating system |
| Python | 3.12 | Backend runtime |
| Node.js | 20 | Frontend + SST |
| Poetry | 2.4.1 | Python dependency management |
| pnpm | latest | JS dependency management |
| Docker | latest | Container runtime |
| AWS CLI | v2 | AWS access |
| Git | system | Source control |

### Running containers on EC2
| Container | Image | Port | Purpose |
|---|---|---|---|
| eluven-postgres | pgvector/pgvector:pg16 | 5432 | Local PostgreSQL + pgvector |

### EC2 environment variables (~/.bashrc)
| Variable | Value |
|---|---|
| DATABASE_URL | postgresql://eluven:eluven_dev_password@localhost:5432/eluven |

---

## Database (Local Dev)

| Item | Detail |
|---|---|
| Engine | PostgreSQL 16 |
| Host | localhost (on EC2) |
| Port | 5432 |
| Database name | eluven |
| Username | eluven |
| Password | eluven_dev_password |
| Extensions | pgvector 0.8.2 |
| Migrations | Alembic — 001_initial applied |

> ⚠️ Production database will be AWS RDS Aurora Serverless v2 — provisioned via SST on first deploy. Credentials will be in AWS Secrets Manager.

---

## AWS Secrets Manager (to be set before first SST deploy)

| Secret name | Purpose | Status |
|---|---|---|
| AnthropicApiKey | Bedrock / Anthropic API key | Not set yet |
| DatabasePassword | RDS production database password | Not set yet |
| NextAuthSecret | NextAuth.js session secret | Not set yet |

---

## GitHub

| Item | Detail |
|---|---|
| Account | origilboa (personal account) |
| Repo | https://github.com/origilboa/eluven (private) |
| Primary email | origilboa@gmail.com |
| Personal access token | Saved in Mac keychain + EC2 git credentials |
| Token scopes | repo + workflow |
| Default branch | main |
| Branching strategy | Feature branches → PR → merge to main |

### GitHub Actions secrets
| Secret | Value | Purpose |
|---|---|---|
| AWS_DEPLOY_ROLE_ARN | arn:aws:iam::124871951150:role/eluven-github-deploy | CI/CD AWS authentication |

---

## Mac Development Environment

| Item | Detail |
|---|---|
| Machine | MacBook Air (Ori's personal Mac) |
| Shell | zsh |
| AWS CLI | v2 — configured with eluven-dev credentials |
| AWS profile | default (us-east-1) |
| Node.js | 26 (via Homebrew) |
| Homebrew | 5.1.14 |
| SSH key | ~/.ssh/eluven-dev |
| SSH config | ~/.ssh/config — Host eluven-dev |
| Shell aliases | ~/.zprofile — eluven-start, eluven-check, eluven-stop |

### Mac shell commands
| Command | What it does |
|---|---|
| `eluven-start` | Starts EC2, updates SSH config with new IP, SSHes in |
| `eluven-check` | Checks running processes before stopping |
| `eluven-stop` | Checks then stops EC2 with confirmation |

---

## SST Infrastructure (defined, not yet deployed)

| Resource | File | Status |
|---|---|---|
| S3 Documents bucket | infra/storage.ts | Defined — deploy pending |
| SQS DocumentProcessing queue | infra/queues.ts | Defined — deploy pending |
| SQS WorkflowExecution queue | infra/queues.ts | Defined — deploy pending |
| RDS Aurora Serverless v2 | infra/database.ts | Defined — deploy pending |
| VPC | infra/database.ts | Defined — deploy pending |
| Secrets | infra/secrets.ts | Defined — deploy pending |

> Run `npx sst deploy --stage production` from EC2 to provision all AWS resources.

---

## Namecheap

| Item | Detail |
|---|---|
| Account | Ori's personal Namecheap account |
| Domain | eluven.ai |
| Expiry | May 29, 2028 |
| Auto-renew | Enabled |
| Privacy | WithheldforPrivacy — enabled, expires May 29, 2027 |
| Nameservers | Custom DNS → Route 53 (AWS) |

---

## Next steps before build

1. SST first deploy — provision S3, SQS, RDS in AWS
2. Set AWS Secrets Manager values (AnthropicApiKey, DatabasePassword, NextAuthSecret)
3. KB & sharing design session (decisions 13, 14, 17, 18)
4. Workflow & instruction design session (decisions 19-23)
5. FinOps session (decision 15)
6. Data model session
7. Begin build sessions
