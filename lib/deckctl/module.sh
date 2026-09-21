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
    if flatpak info --user "$app" >/dev/null 2>&1; then
      flatpak update --user -y "$app"
    else
      echo "[skip] $app is installed system-wide; manage its updates in Discover"
    fi
  else
    flatpak install --user -y flathub "$app"
  fi
}

# Desktop choices are separate from presence checks for shared app dependencies.
desktop_app_install() { PYTHONPATH="$DECKCTL_ROOT/lib" python3 -m deckctl.apps install "$1"; }
desktop_app_satisfied() { PYTHONPATH="$DECKCTL_ROOT/lib" python3 -m deckctl.apps verify "$1"; }

component_selected() { PYTHONPATH="$DECKCTL_ROOT/lib" python3 -m deckctl.component_options "$1" "$2"; }
