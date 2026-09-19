#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'HELP'
NAME
  uninstall.sh — Explain supported uninstall and data retention.
SYNOPSIS
  ./uninstall.sh [--help]
DESCRIPTION
  Read-only guidance. No bulk removal occurs. Use vendor uninstall paths; personal saves/backups are retained.
EXIT STATUS
  0 on completion; nonzero on operational failure.
SEE ALSO
  deckctl help; docs/SCRIPTS.md
HELP
  exit 0
fi
cat <<'EOF'
No destructive one-shot uninstall is provided in v0.2.26.
Use each vendor's supported uninstall path and modules/<module>/README.md.
Personal saves/backups are never removed automatically.
EOF
