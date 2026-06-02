#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
source "${SCRIPT_DIR}/config.sh"

CONNECT=0
SKIP_EC2=0

usage() {
  cat <<EOF
Usage: $(basename "$0") [options]

Resume billable Eluven resources after a stop.

  1. Start EC2 dev server (unless --skip-ec2)
  2. Start RDS and wait until available
  3. Scale ECS API service to ${ELUVEN_ECS_DESIRED_COUNT} task(s)
  4. Optionally SSH in (--connect)

Options:
  -y, --yes        Skip confirmation prompts
  --connect        Update ~/.ssh/config and SSH to EC2 when ready
  --skip-ec2       Do not start EC2 (already running)
  -h, --help       Show this help

After start, allow 2–5 minutes for ECS rollout before using ${ELUVEN_APP_URL}.
EOF
}

update_ssh_config() {
  local ip=$1
  local config="${HOME}/.ssh/config"
  local tmp
  tmp="$(mktemp)"

  mkdir -p "${HOME}/.ssh"
  touch "$config"

  if grep -q "^Host ${ELUVEN_SSH_HOST}$" "$config"; then
    awk -v host="$ELUVEN_SSH_HOST" -v ip="$ip" '
      BEGIN { inblock = 0 }
      /^Host / { inblock = ($2 == host) }
      inblock && /^[[:space:]]*HostName / { sub(/HostName .*/, "HostName " ip) }
      { print }
    ' "$config" >"$tmp"
  else
    cat "$config" >"$tmp"
    cat >>"$tmp" <<EOF

Host ${ELUVEN_SSH_HOST}
  HostName ${ip}
  User ${ELUVEN_SSH_USER}
  IdentityFile ${ELUVEN_SSH_KEY}
EOF
  fi

  mv "$tmp" "$config"
  chmod 600 "$config"
  log "Updated SSH config: ${ELUVEN_SSH_HOST} -> ${ip}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y | --yes) ELUVEN_YES=1; shift ;;
    --connect) CONNECT=1; shift ;;
    --skip-ec2) SKIP_EC2=1; shift ;;
    -h | --help) usage; exit 0 ;;
    *) die "Unknown option: $1" ;;
  esac
done

if ! confirm "Start EC2, RDS, and ECS API service?"; then
  log "Cancelled."
  exit 0
fi

ec2_ip=""

if [[ "$SKIP_EC2" -eq 0 ]]; then
  ec2_state=$(aws_cli ec2 describe-instances \
    --instance-ids "$ELUVEN_EC2_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text)

  if [[ "$ec2_state" == "stopped" ]]; then
    log "Starting EC2 ${ELUVEN_EC2_INSTANCE_ID}..."
    aws_cli ec2 start-instances --instance-ids "$ELUVEN_EC2_INSTANCE_ID" --output text >/dev/null
    wait_for "EC2 to run" [[ "$(ec2_status)" == "running" ]]
  else
    log "EC2 already ${ec2_state}."
  fi

  ec2_ip=$(aws_cli ec2 describe-instances \
    --instance-ids "$ELUVEN_EC2_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)
  log "EC2 public IP: ${ec2_ip}"
  update_ssh_config "$ec2_ip"
else
  log "Skipping EC2 start (--skip-ec2)."
fi

rds_state=$(aws_cli rds describe-db-instances \
  --db-instance-identifier "$ELUVEN_RDS_INSTANCE_ID" \
  --query 'DBInstances[0].DBInstanceStatus' \
  --output text)

if [[ "$rds_state" == "stopped" ]]; then
  log "Starting RDS ${ELUVEN_RDS_INSTANCE_ID}..."
  aws_cli rds start-db-instance \
    --db-instance-identifier "$ELUVEN_RDS_INSTANCE_ID" \
    --output text >/dev/null
  wait_for "RDS to become available (this can take several minutes)" [[ "$(rds_status)" == "available" ]]
elif [[ "$rds_state" == "available" ]]; then
  log "RDS already available."
else
  wait_for "RDS to become available (current state: ${rds_state})" [[ "$(rds_status)" == "available" ]]
fi

log "Scaling ECS ${ELUVEN_ECS_SERVICE} to ${ELUVEN_ECS_DESIRED_COUNT}..."
aws_cli ecs update-service \
  --cluster "$ELUVEN_ECS_CLUSTER" \
  --service "$ELUVEN_ECS_SERVICE" \
  --desired-count "$ELUVEN_ECS_DESIRED_COUNT" \
  --force-new-deployment \
  --output text >/dev/null

wait_for "ECS service to reach desired count" [[ "$(ecs_running_count)" == "$(ecs_desired_count)" && "$(ecs_running_count)" -ge 1 ]]

echo
log "Start complete. App should be reachable at ${ELUVEN_APP_URL} shortly."
"${SCRIPT_DIR}/eluven-status.sh"

if [[ "$CONNECT" -eq 1 ]]; then
  if [[ -z "$ec2_ip" ]]; then
    ec2_ip=$(aws_cli ec2 describe-instances \
      --instance-ids "$ELUVEN_EC2_INSTANCE_ID" \
      --query 'Reservations[0].Instances[0].PublicIpAddress' \
      --output text)
  fi
  log "Connecting via SSH..."
  exec ssh -i "$ELUVEN_SSH_KEY" "${ELUVEN_SSH_USER}@${ec2_ip}"
fi
