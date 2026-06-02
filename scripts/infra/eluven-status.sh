#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.sh
source "${SCRIPT_DIR}/config.sh"

ec2_state=$(aws_cli ec2 describe-instances \
  --instance-ids "$ELUVEN_EC2_INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].State.Name' \
  --output text)
ec2_ip=$(aws_cli ec2 describe-instances \
  --instance-ids "$ELUVEN_EC2_INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text 2>/dev/null || echo "n/a")

ecs_desired=$(aws_cli ecs describe-services \
  --cluster "$ELUVEN_ECS_CLUSTER" \
  --services "$ELUVEN_ECS_SERVICE" \
  --query 'services[0].desiredCount' \
  --output text)
ecs_running=$(aws_cli ecs describe-services \
  --cluster "$ELUVEN_ECS_CLUSTER" \
  --services "$ELUVEN_ECS_SERVICE" \
  --query 'services[0].runningCount' \
  --output text)

rds_state=$(aws_cli rds describe-db-instances \
  --db-instance-identifier "$ELUVEN_RDS_INSTANCE_ID" \
  --query 'DBInstances[0].DBInstanceStatus' \
  --output text)

cat <<EOF
Eluven infrastructure status (${ELUVEN_AWS_REGION})

  EC2 dev server     ${ELUVEN_EC2_INSTANCE_ID}
    state:            ${ec2_state}
    public IP:        ${ec2_ip}

  ECS API service    ${ELUVEN_ECS_SERVICE} @ ${ELUVEN_ECS_CLUSTER}
    desired/running:  ${ecs_desired} / ${ecs_running}

  RDS PostgreSQL     ${ELUVEN_RDS_INSTANCE_ID}
    state:            ${rds_state}

  App URL            ${ELUVEN_APP_URL}
    (app works only when ECS >= 1 and RDS is available)

Fixed baseline cost (always on): VPC + 8 interface endpoints (~\$50–60/month).
Stop scripts below reduce EC2, ECS Fargate, and RDS spend while idle.
EOF
