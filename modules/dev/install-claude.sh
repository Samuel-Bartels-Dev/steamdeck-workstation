#!/usr/bin/env bash
# Native, user-space Claude Code. Authentication is a separate interactive step.
set -euo pipefail

claude_bin="$HOME/.local/bin/claude"
# Reserve room for a download, staged version and installation overhead.
python3 - "$HOME" <<'PY'
import shutil
import sys
if shutil.disk_usage(sys.argv[1]).free < 1024 ** 3:
    sys.exit('Claude Code needs at least 1 GiB free in your home filesystem for installation/update.')
PY

if [[ -x "$claude_bin" ]] && "$claude_bin" --version >/dev/null 2>&1; then
  echo "Checking Claude Code for updates..."
  "$claude_bin" update
elif [[ -e "$claude_bin" || -L "$claude_bin" ]]; then
  echo "[error] Existing ~/.local/bin/claude is not runnable; repair or move it before installing." >&2
  exit 1
else
  # Keep the installer on the checked filesystem and remove our temporary files.
  claude_tmp="$(mktemp -d "$HOME/.claude-install.XXXXXX")"
  trap 'rm -rf -- "$claude_tmp"' EXIT
  curl --fail --location --proto '=https' --tlsv1.2 --retry 3 \
    https://claude.ai/install.sh -o "$claude_tmp/install.sh"
  bash "$claude_tmp/install.sh"
fi
"$claude_bin" --version
printf '\nClaude Code is installed. Run: claude\nFollow the browser sign-in prompts. A supported Claude account or API billing is required.\n'
