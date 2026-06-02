#!/usr/bin/env bash
# Print shell aliases for Mac (~/.zshrc for interactive zsh, or ~/.zprofile for login shells).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cat <<EOF
# Eluven infrastructure scripts
export ELUVEN_REPO="${REPO_ROOT}"
alias eluven-status='bash "\${ELUVEN_REPO}/scripts/infra/eluven-status.sh"'
alias eluven-check='bash "\${ELUVEN_REPO}/scripts/infra/eluven-check.sh"'
alias eluven-stop='bash "\${ELUVEN_REPO}/scripts/infra/eluven-stop.sh"'
alias eluven-start='bash "\${ELUVEN_REPO}/scripts/infra/eluven-start.sh" --connect'
EOF
