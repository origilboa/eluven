# Infrastructure Runbook

## AWS Account
- **Account ID:** 124871951150
- **Account name:** eluven
- **Root email:** origilboa@gmail.com (personal — recovery only)
- **Region:** us-east-1

## Key resources

| Resource | Name/ID | Notes |
|---|---|---|
| EC2 key pair | eluven-dev | Private key at ~/.ssh/eluven-dev |
| Security group | sg-014bad2a06964d191 | SSH on port 22 |
| EC2 instance | TBD — pending quota approval | t3.xlarge, Ubuntu 24 LTS |

## Dev server

### Start
```bash
eluven-start
```
Starts the EC2, waits until ready, updates SSH config with current IP, SSHes in.

### Check before stopping
```bash
eluven-check
```
Shows active sessions, CPU usage, running processes.

### Stop
```bash
eluven-stop
```
Runs check first, asks for confirmation, then stops the instance.

## Cost controls

| Budget | Threshold | Alert email |
|---|---|---|
| Eluven Monthly Total | $50 | ori.gilboa@eluven.ai |
| Eluven Bedrock Monthly Budget | $30 | ori.gilboa@eluven.ai |
| Eluven Infrastructure Monthly Budget | $20 | ori.gilboa@eluven.ai |
| Anomaly Detection | $20 spike | ori.gilboa@eluven.ai |

## GitHub
- **Repo:** https://github.com/origilboa/eluven
- **Branching:** feature branches off main
- **CI/CD:** GitHub Actions — branch.yml, pr.yml, deploy.yml

## SST
- **App name:** eluven
- **Home:** aws
- **Production removal:** retain (never auto-delete production resources)

## Secrets (AWS Secrets Manager)
Set these before first deploy:
- AnthropicApiKey
- DatabasePassword  
- NextAuthSecret

## TODO — complete during infrastructure session
- [ ] Launch EC2 (pending quota approval)
- [ ] Install dev tools on EC2 (Node.js, Python, Poetry, pnpm)
- [ ] Install OrbStack + PostgreSQL + pgvector on EC2
- [ ] Clone repo on EC2
- [ ] Configure AWS credentials on EC2
- [ ] Initialise Alembic + first migration
- [ ] Migrate eluven.ai DNS to Route 53
- [ ] Provision SSL via ACM
- [ ] Test SST dev mode
