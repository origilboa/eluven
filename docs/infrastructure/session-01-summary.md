# Infrastructure Session 01 — Summary

Date: May 30, 2026
Status: Partially complete — continue in next session

## What was completed

### AWS Account
- Account created, name: eluven, ID: 124871951150
- Root user secured with MFA
- IAM user `eluven-dev` created with AdministratorAccess
- AWS CLI configured on Mac with eluven-dev credentials
- Account upgraded from Free Plan to standard pay-as-you-go
- $100 free credits active, valid until Nov 30, 2026

### Google Workspace
- `ori.gilboa@eluven.ai` created and active
- Used for all Eluven platform communications

### GitHub
- Repo: https://github.com/origilboa/eluven (private)
- Full folder structure committed
- `.cursor/rules/` — all 8 .mdc rules files committed
- `/docs/spec/` — concept doc and process plan committed
- Personal access token configured with repo + workflow scopes
- Credentials saved to Mac keychain

### Cost controls
- Budget: Eluven Monthly Total — $50 alert
- Budget: Eluven Bedrock Monthly Budget — $30 alert
- Budget: Eluven Infrastructure Monthly Budget — $20 alert
- Cost Anomaly Monitor: Eluven Anomaly Monitor — $20 spike alert
- All alerts → ori.gilboa@eluven.ai

### AWS Bedrock
- Model access confirmed auto-enabled (no manual activation needed)
- Anthropic models available on first invocation

### EC2 Dev Server
- Instance ID: i-02e28fbb277628ada
- Instance type: t3.xlarge
- AMI: Ubuntu 24.04 LTS (ami-067bcf851477ebb78)
- Region: us-east-1
- Public IP: 54.175.59.14 (note: this changes on stop/start — eluven-start handles this)
- Security group: sg-014bad2a06964d191 (SSH port 22 open)
- Storage: 50GB gp3
- Key pair: eluven-dev (~/.ssh/eluven-dev on Mac)
- Status: running, Ubuntu upgraded to latest packages

### Mac tooling
- Homebrew 5.1.14 installed
- Node.js 26 installed
- AWS CLI v2 installed and configured
- SSH config: ~/.ssh/config — Host eluven-dev configured
- Shell aliases in ~/.zprofile:
  - `eluven-start` — starts EC2, updates SSH config with new IP, SSHes in
  - `eluven-check` — checks running processes before stopping
  - `eluven-stop` — checks then stops EC2

### SST
- Initialised in repo root
- sst.config.ts written
- infra/secrets.ts — AnthropicApiKey, DatabasePassword, NextAuthSecret
- infra/storage.ts — Documents S3 bucket with versioning
- infra/queues.ts — DocumentProcessing and WorkflowExecution SQS queues
- infra/database.ts — Aurora Serverless v2 PostgreSQL with VPC

### GitHub Actions CI/CD
- .github/workflows/branch.yml — lint + unit tests on branch push
- .github/workflows/pr.yml — full tests on PR to main
- .github/workflows/deploy.yml — deploy to production on merge to main

### Backend skeleton
- backend/pyproject.toml — Poetry project with all dependencies defined
- backend/core/config.py — Pydantic settings
- backend/core/logging.py — structured JSON logging
- backend/alembic.ini — Alembic configuration
- backend/alembic/env.py — Alembic environment
- backend/alembic/versions/001_initial.py — first migration enabling pgvector
- scripts/seed.py — seed script skeleton with --dev, --test, --clear modes

## What remains for next session

### On EC2 (do first)
- [ ] Install dev tools: Node.js, Python 3.12, Poetry, pnpm
- [ ] Install OrbStack
- [ ] Run PostgreSQL + pgvector container via OrbStack
- [ ] Configure AWS credentials on EC2
- [ ] Clone eluven repo onto EC2
- [ ] Install backend Python dependencies via Poetry
- [ ] Run first Alembic migration against local PostgreSQL
- [ ] Test SST dev mode connects to real AWS Bedrock, S3, SQS

### DNS & SSL
- [ ] Migrate eluven.ai DNS from Namecheap to Route 53
- [ ] Migrate MX records (Google Workspace email) to Route 53
- [ ] Provision SSL certificate via AWS ACM

### GitHub Actions
- [ ] Create AWS_DEPLOY_ROLE_ARN IAM role for GitHub Actions deployment
- [ ] Add secret to GitHub repo

## How to resume next session

1. Start the EC2: run `eluven-start` in Mac Terminal
2. Note: public IP changes on every start — eluven-start handles the SSH config update automatically
3. SSH in and continue with EC2 setup steps above
4. Load this document + concept doc + process plan at session start

## Key credentials location
- AWS CLI credentials: ~/.aws/credentials (Mac)
- EC2 SSH key: ~/.ssh/eluven-dev (Mac)
- GitHub token: saved in Mac keychain
- Google Workspace: ori.gilboa@eluven.ai
