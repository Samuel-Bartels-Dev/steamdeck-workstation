#!/usr/bin/env bash
set -euo pipefail
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
app_status=0
flatpak_install com.github.tchx84.Flatseal || app_status=1
flatpak_install app.zen_browser.zen || app_status=1
exit "$app_status"
