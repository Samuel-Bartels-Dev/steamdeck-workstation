#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'HELP'
NAME
  install.sh — Provision a Steam Deck using the normal guided installer.
SYNOPSIS
  ./install.sh [--help]
DESCRIPTION
  Validates the repo, installs a persistent control plane, detects hardware, runs enabled modules, and offers resumable vendor/account setup. Run as the normal user in Desktop Mode. Internet is needed for vendor downloads; sudo is requested by specific vendors only. A failed module produces a nonzero final exit status, while the guided flow remains available.
EXIT STATUS
  0 on completion; nonzero on operational failure.
SEE ALSO
  deckctl help; docs/SCRIPTS.md
HELP
  exit 0
fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
printf '\nSteam Deck Workstation %s\n' "$(cat VERSION)"
printf '%s\n' '----------------------------------------'
if [[ $EUID -eq 0 ]]; then echo "Do not run install.sh as root." >&2; exit 1; fi
command -v python3 >/dev/null || { echo "python3 is required; SteamOS should provide it." >&2; exit 1; }

# Release archives preserve executable modes. Sourced shell configuration is
# intentionally non-executable; do not normalize permissions before validation.
printf '\nRunning pre-install checks; software installation starts after these pass.\n'
if ! ./bin/deckctl repo validate; then
  printf '\nPre-install checks failed. Provisioning has not started. Save the error output for troubleshooting.\n' >&2
  exit 1
fi
printf '\nPre-install checks passed. Starting workstation setup.\n'

if [[ "${DECKCTL_REEXEC:-0}" != "1" ]]; then
  ./bin/deckctl update preview --source "$ROOT"
  read -r -p "Apply this release? [Y/n] " upgrade_answer
  if [[ "${upgrade_answer:-Y}" =~ ^[Nn]$ ]]; then exit 0; fi
fi
PERSIST_ROOT="$(./tools/install-control-plane "$ROOT")"
ROOT_REAL="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$ROOT")"
PERSIST_REAL="$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$PERSIST_ROOT")"
if [[ "$ROOT_REAL" != "$PERSIST_REAL" && "${DECKCTL_REEXEC:-0}" != "1" ]]; then
  exec env DECKCTL_REEXEC=1 "$PERSIST_ROOT/install.sh"
fi

printf '\nPersistent command installed: %s\n' "$HOME/.local/bin/deckctl"
printf 'Open a new terminal after setup for aliases: dplan, dverify, dsetup, dplugins, etc.\n'

if [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]] && { command -v qml6 >/dev/null || command -v qml >/dev/null; }; then
  ./bin/deckctl detect
  ./bin/deckctl profile auto || true
  exec ./bin/deckctl setup customize
fi
./bin/deckctl setup customize

./bin/deckctl detect
./bin/deckctl profile auto || true
printf '\nCurrent plan/status:\n'; ./bin/deckctl plan
printf '\nThis provisioning pass installs safe user-space packages and stages guided third-party installers.\n'
read -r -p "Continue? [Y/n] " ans
if [[ "${ans:-Y}" =~ ^[Nn]$ ]]; then exit 0; fi
apply_status=0
./bin/deckctl setup install || apply_status=$?
printf '\nPost-install status:\n'; ./bin/deckctl verify || true
./bin/deckctl setup status
printf '\nThe remaining vendor/account steps are guided. deckctl will launch each installer/app for you.\n'
read -r -p "Start guided setup now? [Y/n] " guided
if [[ ! "${guided:-Y}" =~ ^[Nn]$ ]]; then
  ./bin/deckctl setup run || apply_status=$?
else
  cat <<'NEXT'

GUIDED SETUP PAUSED
Run: deckctl setup run
Or double-click "Continue Steam Deck Setup" on the Desktop.
NEXT
fi

# Optional development integration owns its own selection, preflight and retry logic.
./bin/deckctl containers provision || apply_status=$?

./bin/deckctl setup report || apply_status=$?
./bin/deckctl ai-workspace guide
exit "$apply_status"
