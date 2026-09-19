#!/usr/bin/env bash
set -euo pipefail
source "$DECKCTL_ROOT/lib/deckctl/module.sh"

app_status=0
flatpak_install com.visualstudio.code || app_status=1
flatpak_install dev.zed.Zed || app_status=1
mkdir -p "$HOME/.config/deckctl" "$HOME/.local/bin"
cp "$DECKCTL_ROOT/modules/dev/distrobox.ini" "$HOME/.config/deckctl/distrobox.ini"

# Codex is a host-level user tool. Do not make it depend on Distrobox/npm.
"$DECKCTL_ROOT/modules/dev/install-codex.sh"

# Distrobox remains the isolated development environment for project dependencies.
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
exit "$app_status"
