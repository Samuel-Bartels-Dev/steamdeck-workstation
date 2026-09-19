#!/usr/bin/env bash
set -u

module_json() {
  local status="$1"; shift
  local message="${1:-}"; shift || true
  python3 - "$status" "$message" <<'PY'
import json,sys
print(json.dumps({"status":sys.argv[1],"message":sys.argv[2]}))
PY
}

have() { command -v "$1" >/dev/null 2>&1; }
flatpak_has() { flatpak info "$1" >/dev/null 2>&1; }
flatpak_install() {
  local app="$1"
  if flatpak_has "$app"; then
    echo "[skip] $app already installed"
  else
    flatpak install --user -y flathub "$app"
  fi
}
