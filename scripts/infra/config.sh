#!/usr/bin/env bash
# Shared configuration for Eluven infrastructure start/stop scripts.
# Override any value via environment variables before calling the scripts.

: "${ELUVEN_AWS_REGION:=us-east-1}"
: "${ELUVEN_EC2_INSTANCE_ID:=i-02e28fbb277628ada}"
: "${ELUVEN_ECS_CLUSTER:=eluven-production-EluvenClusterCluster-bcxhvdvx}"
: "${ELUVEN_ECS_SERVICE:=Api}"
: "${ELUVEN_ECS_DESIRED_COUNT:=1}"
: "${ELUVEN_RDS_INSTANCE_ID:=eluven-production-databaseinstance-vmdmnvvm}"
: "${ELUVEN_SSH_HOST:=eluven-dev}"
: "${ELUVEN_SSH_USER:=ubuntu}"
: "${ELUVEN_SSH_KEY:=${HOME}/.ssh/eluven-dev}"
: "${ELUVEN_APP_URL:=https://app.eluven.ai}"

export ELUVEN_AWS_REGION ELUVEN_EC2_INSTANCE_ID ELUVEN_ECS_CLUSTER ELUVEN_ECS_SERVICE
export ELUVEN_ECS_DESIRED_COUNT ELUVEN_RDS_INSTANCE_ID ELUVEN_SSH_HOST ELUVEN_SSH_USER
export ELUVEN_SSH_KEY ELUVEN_APP_URL

aws_cli() {
  aws --region "$ELUVEN_AWS_REGION" "$@"
}

log() {
  printf '[eluven] %s\n' "$*"
}

warn() {
  printf '[eluven] WARNING: %s\n' "$*" >&2
}

die() {
  printf '[eluven] ERROR: %s\n' "$*" >&2
  exit 1
}

confirm() {
  local prompt=$1
  if [[ "${ELUVEN_YES:-}" == "1" ]]; then
    return 0
  fi
  read -r -p "$prompt [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]]
}

wait_for() {
  local description=$1
  shift
  log "Waiting for ${description}..."
  until eval "$*"; do
    sleep 10
  done
}

rds_status() {
  aws_cli rds describe-db-instances \
    --db-instance-identifier "$ELUVEN_RDS_INSTANCE_ID" \
    --query 'DBInstances[0].DBInstanceStatus' \
    --output text
}

ec2_status() {
  aws_cli ec2 describe-instances \
    --instance-ids "$ELUVEN_EC2_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text
}

ecs_running_count() {
  aws_cli ecs describe-services \
    --cluster "$ELUVEN_ECS_CLUSTER" \
    --services "$ELUVEN_ECS_SERVICE" \
    --query 'services[0].runningCount' \
    --output text
}

ecs_desired_count() {
  aws_cli ecs describe-services \
    --cluster "$ELUVEN_ECS_CLUSTER" \
    --services "$ELUVEN_ECS_SERVICE" \
    --query 'services[0].desiredCount' \
    --output text
}
