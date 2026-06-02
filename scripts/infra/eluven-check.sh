#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
source "${SCRIPT_DIR}/config.sh"

log "Pre-stop checks"
"${SCRIPT_DIR}/eluven-status.sh"
echo

ec2_state=$(aws_cli ec2 describe-instances \
  --instance-ids "$ELUVEN_EC2_INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text)

if [[ "$ec2_state" == "running" ]]; then
  ec2_ip=$(aws_cli ec2 describe-instances \
    --instance-ids "$ELUVEN_EC2_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].PublicIpAddress' \
    --output text)

  if [[ -f "$ELUVEN_SSH_KEY" ]]; then
    log "Checking EC2 for active sessions and git status..."
    if ssh -i "$ELUVEN_SSH_KEY" -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new \
      "${ELUVEN_SSH_USER}@${ec2_ip}" 'bash -s' <<'REMOTE'; then
who | grep -v "^ubuntu " || true
echo "--- git status (~/eluven) ---"
if [[ -d ~/eluven/.git ]]; then
  git -C ~/eluven status --short
else
  echo "repo not found at ~/eluven"
fi
REMOTE
      :
    else
      warn "Could not SSH to EC2 — review manually before stopping."
    fi
  else
    warn "SSH key not found at ${ELUVEN_SSH_KEY} — skipping remote checks."
  fi
fi

log "Review complete. Run eluven-stop.sh when ready to pause billable resources."
