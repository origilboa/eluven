#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
source "${SCRIPT_DIR}/config.sh"

SKIP_CHECK=0
SKIP_EC2=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Pause billable Eluven resources to save cost while not working.

  1. Scale ECS API service to 0 tasks
  2. Stop RDS PostgreSQL (auto-restarts after 7 days if not started manually)
  3. Stop EC2 dev server (unless --skip-ec2)

Options:
  -y, --yes        Skip confirmation prompts
  --skip-check     Do not run eluven-check.sh first
  --skip-ec2       Leave EC2 running (e.g. when running this from EC2 over SSH)
  -h, --help       Show this help

Run from your Mac (recommended) so EC2 can be stopped safely.
${ELUVEN_APP_URL} will be unavailable until eluven-start.sh is run.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y | --yes) ELUVEN_YES=1; shift ;;
    --skip-check) SKIP_CHECK=1; shift ;;
    --skip-ec2) SKIP_EC2=1; shift ;;
    -h | --help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

if [[ "$SKIP_CHECK" -eq 0 ]]; then
  "${SCRIPT_DIR}/eluven-check.sh"
  echo
fi

if ! confirm "Stop production API, RDS, and EC2 dev server?"; then
  log "Cancelled."
  exit 0
fi

ecs_desired=$(aws_cli ecs describe-services \
  --cluster "$ELUVEN_ECS_CLUSTER" \
  --services "$ELUVEN_ECS_SERVICE" \
  --query 'services[0].desiredCount' \
  --output text)

if [[ "$ecs_desired" != "0" ]]; then
  log "Scaling ECS ${ELUVEN_ECS_SERVICE} to 0 tasks..."
  aws_cli ecs update-service \
    --cluster "$ELUVEN_ECS_CLUSTER" \
    --service "$ELUVEN_ECS_SERVICE" \
    --desired-count 0 \
    --output text >/dev/null
  wait_for "ECS tasks to stop" [[ "$(ecs_running_count)" == "0" ]]
else
  log "ECS already scaled to 0."
fi

rds_state=$(aws_cli rds describe-db-instances \
  --db-instance-identifier "$ELUVEN_RDS_INSTANCE_ID" \
  --query 'DBInstances[0].DBInstanceStatus' \
  --output text)

if [[ "$rds_state" == "available" ]]; then
  log "Stopping RDS ${ELUVEN_RDS_INSTANCE_ID}..."
  aws_cli rds stop-db-instance \
    --db-instance-identifier "$ELUVEN_RDS_INSTANCE_ID" \
    --output text >/dev/null
  wait_for "RDS to stop" [[ "$(rds_status)" == "stopped" ]]
elif [[ "$rds_state" == "stopped" ]]; then
  log "RDS already stopped."
else
  warn "RDS state is ${rds_state}; skipping stop."
fi

if [[ "$SKIP_EC2" -eq 0 ]]; then
  ec2_state=$(aws_cli ec2 describe-instances \
    --instance-ids "$ELUVEN_EC2_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text)

  if [[ "$ec2_state" == "running" ]]; then
    log "Stopping EC2 ${ELUVEN_EC2_INSTANCE_ID}..."
    aws_cli ec2 stop-instances --instance-ids "$ELUVEN_EC2_INSTANCE_ID" --output text >/dev/null
    wait_for "EC2 to stop" [[ "$(ec2_status)" == "stopped" ]]
  else
    log "EC2 already ${ec2_state}."
  fi
else
  warn "Skipping EC2 stop (--skip-ec2). Stop EC2 from your Mac when you disconnect."
fi

echo
log "Stop complete."
"${SCRIPT_DIR}/eluven-status.sh"
