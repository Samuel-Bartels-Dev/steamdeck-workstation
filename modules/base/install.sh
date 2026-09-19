#!/usr/bin/env bash
set -euo pipefail
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
have flatpak || { echo "Flatpak is missing; repair SteamOS before continuing." >&2; exit 1; }
if ! flatpak remotes --user --columns=name | grep -qx flathub; then flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo; fi
mkdir -p "$DECKCTL_STATE" "$DECKCTL_CONFIG"

PYTHONPATH="$DECKCTL_ROOT/lib" python3 -c 'from deckctl.desktop import apply; raise SystemExit(apply())'
