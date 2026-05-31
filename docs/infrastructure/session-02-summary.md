# Infrastructure Session 02 — Summary

Date: May 31, 2026
Status: Infrastructure complete — ready to begin data model session

## What was completed this session

### EC2 Dev Server — fully configured
- Python 3.12 installed
- Node.js 20 installed
- Poetry 2.4.1 installed
- pnpm installed
- Docker installed
- PostgreSQL + pgvector container running (pgvector 0.8.2)
- AWS CLI installed and configured
- Repo cloned at ~/eluven
- Backend Python dependencies installed via Poetry
- First Alembic migration applied — pgvector extension enabled
- AWS Bedrock accessible and tested
- Git configured with ori.gilboa@eluven.ai
- DATABASE_URL set in ~/.bashrc

### DNS & SSL
- Route 53 hosted zone created: Z06614832D7DMEV9IQTMN
- eluven.ai nameservers pointing to Route 53 (set in Namecheap)
- Google Workspace MX records added to Route 53
- SSL certificate issued via ACM
- Certificate ARN: arn:aws:acm:us-east-1:124871951150:certificate/e479bebb-cdd6-4909-a2c5-8039ed3c2241
- Covers eluven.ai and *.eluven.ai

### GitHub Actions
- OIDC provider created for GitHub Actions authentication
- IAM role created: eluven-github-deploy
- Role ARN: arn:aws:iam::124871951150:role/eluven-github-deploy
- AdministratorAccess attached to deploy role
- AWS_DEPLOY_ROLE_ARN secret added to GitHub repo

## Current infrastructure state

| Resource | Details | Status |
|---|---|---|
| EC2 | i-02e28fbb277628ada, t3.xlarge, Ubuntu 24.04 | Ready |
| PostgreSQL | Docker container, port 5432, db: eluven | Running |
| pgvector | 0.8.2, enabled via migration | Ready |
| Route 53 | Z06614832D7DMEV9IQTMN, eluven.ai | Active |
| SSL Certificate | *.eluven.ai + eluven.ai | Issued |
| S3 Bucket | Defined in SST — not yet deployed | Pending SST deploy |
| SQS Queues | Defined in SST — not yet deployed | Pending SST deploy |
| RDS Database | Defined in SST — not yet deployed | Pending SST deploy |

## What remains before build sessions

### SST first deploy
- Run `npx sst deploy --stage production` to provision S3, SQS, RDS
- Set secrets in AWS Secrets Manager: AnthropicApiKey, DatabasePassword, NextAuthSecret
- Run `npx sst dev` to test dev mode connects to real AWS services

### Before data model session
- Resolve open decisions 13, 14, 17, 18, 19, 20, 21, 22, 23 (KB & sharing, workflow design)
- FinOps session (decision 15)

## How to resume next session
1. Run `eluven-start` on Mac to start EC2 and SSH in
2. PostgreSQL starts automatically (Docker restart policy: unless-stopped)
3. DATABASE_URL is set in ~/.bashrc automatically
