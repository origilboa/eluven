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
| EC2 instance | i-02e28fbb277628ada | t3.xlarge, Ubuntu 24 LTS |
| Production app | https://app.eluven.ai | CloudFront + Lambda + ECS API |
| RDS | eluven-production-databaseinstance-vmdmnvvm | db.t3.micro |
| ECS cluster | eluven-production-EluvenClusterCluster-bcxhvdvx | Service: Api |

## Start / stop (save cost when not working)

Scripts live in **`scripts/infra/`**. See [scripts/infra/README.md](../../scripts/infra/README.md) for full detail.

### One-time Mac setup

```bash
bash ~/eluven/scripts/infra/install-mac-aliases.sh >> ~/.zprofile
source ~/.zprofile
```

Requires AWS CLI on your Mac.

### Daily use (from Mac Terminal)

| Command | Action |
|---|---|
| `eluven-status` | Show EC2, ECS, RDS state |
| `eluven-check` | Pre-stop check (git status on EC2, etc.) |
| `eluven-stop` | Scale ECS to 0, stop RDS, stop EC2 |
| `eluven-start` | Start EC2 + RDS + ECS, update SSH config, connect |

**While stopped:** app.eluven.ai is down. VPC endpoints (~$50–60/mo) still bill.

**RDS:** auto-restarts after 7 days if left stopped.

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
- **Deploy:** `npx sst deploy --stage production` (from EC2 ~/eluven)

## Secrets (AWS Secrets Manager)
- AnthropicApiKey
- DatabasePassword
- NextAuthSecret
