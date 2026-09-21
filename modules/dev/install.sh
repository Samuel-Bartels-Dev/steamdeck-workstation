#!/usr/bin/env bash
set -euo pipefail
source "$DECKCTL_ROOT/lib/deckctl/module.sh"

app_status=0
desktop_app_install com.visualstudio.code || app_status=1
desktop_app_install dev.zed.Zed || app_status=1
mkdir -p "$HOME/.config/deckctl" "$HOME/.local/bin"
cp "$DECKCTL_ROOT/modules/dev/distrobox.ini" "$HOME/.config/deckctl/distrobox.ini"

# Codex is a host-level user tool. Do not make it depend on Distrobox/npm.
if component_selected dev codex; then "$DECKCTL_ROOT/modules/dev/install-codex.sh"; fi

if component_selected dev claude-code; then
  "$DECKCTL_ROOT/modules/dev/install-claude.sh" || app_status=1
fi

# Distrobox remains the isolated development environment for project dependencies.
if component_selected dev distrobox; then
if have distrobox && have podman; then
  if ! distrobox list 2>/dev/null | grep -Eq '(^|[[:space:]])deck-dev([[:space:]]|$)'; then
    echo "Creating deck-dev Distrobox..."
    distrobox assemble create --file "$HOME/.config/deckctl/distrobox.ini" || true
  else
    echo "[skip] deck-dev already exists"
  fi
else
  echo "[warn] Distrobox/Podman not both visible on PATH. Codex is installed independently; deck-dev can be repaired later with deckctl doctor dev."
fi
fi
if component_selected dev docker; then
  "$DECKCTL_ROOT/bin/deckctl" containers provision || app_status=1
fi
exit "$app_status"
