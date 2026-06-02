# Eluven infrastructure start/stop scripts

Pause and resume billable AWS resources when you are not working.

## What gets stopped

| Resource | Approx. savings when stopped |
|----------|------------------------------|
| EC2 dev server (t3.xlarge) | ~\$0.17/hr |
| ECS Fargate API (1 task) | ~\$0.04/hr |
| RDS PostgreSQL (db.t3.micro) | ~\$0.02/hr |

**Still billing while "stopped":** VPC, 8 interface endpoints, S3, CloudFront/Lambda idle, Route 53 (~\$50–60/month baseline).

**While stopped:** https://app.eluven.ai is unavailable until you run `eluven-start.sh`.

## Setup (Mac — run once)

Add to `~/.zprofile` (adjust path if your repo clone differs):

```bash
export ELUVEN_REPO="${HOME}/eluven"   # or wherever you clone on Mac
alias eluven-status='bash "${ELUVEN_REPO}/scripts/infra/eluven-status.sh"'
alias eluven-check='bash "${ELUVEN_REPO}/scripts/infra/eluven-check.sh"'
alias eluven-stop='bash "${ELUVEN_REPO}/scripts/infra/eluven-stop.sh"'
alias eluven-start='bash "${ELUVEN_REPO}/scripts/infra/eluven-start.sh" --connect'
```

Requires AWS CLI configured on your Mac (`aws sts get-caller-identity`).

If you only use SSH Remote on EC2 (no local clone), clone the repo on Mac once for these scripts, or copy `scripts/infra/` to `~/bin/`.

## Daily workflow

### End of day (from Mac Terminal)

```bash
eluven-check    # optional — git status on EC2, resource summary
eluven-stop     # scales ECS to 0, stops RDS, stops EC2
```

### Start of day (from Mac Terminal)

```bash
eluven-start    # starts EC2 + RDS + ECS, updates SSH config, opens SSH
```

Or without auto-SSH:

```bash
bash ~/eluven/scripts/infra/eluven-start.sh
```

### Status only

```bash
eluven-status
```

## Running from EC2 over SSH

If you are already on the dev server, use `--skip-ec2` so you are not cut off mid-command:

```bash
bash ~/eluven/scripts/infra/eluven-stop.sh --skip-ec2
# then exit SSH and run full stop from Mac, or stop EC2 from Mac later
```

## Options

| Script | Flags |
|--------|--------|
| `eluven-stop.sh` | `-y` skip prompts, `--skip-check`, `--skip-ec2` |
| `eluven-start.sh` | `-y`, `--connect`, `--skip-ec2` |

## RDS note

Stopped RDS instances automatically restart after **7 days**. Run `eluven-stop` again if you stay idle longer.

## Configuration

Edit `config.sh` or set environment variables:

- `ELUVEN_EC2_INSTANCE_ID`
- `ELUVEN_ECS_CLUSTER`
- `ELUVEN_ECS_SERVICE`
- `ELUVEN_RDS_INSTANCE_ID`
