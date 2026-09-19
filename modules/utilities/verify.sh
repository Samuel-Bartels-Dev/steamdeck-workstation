#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
missing=()
flatpak_has com.github.tchx84.Flatseal || missing+=("Flatseal")
flatpak_has app.zen_browser.zen || missing+=("Zen Browser")
if (( ${#missing[@]} )); then
  module_json NOT_INSTALLED "Missing desktop apps: ${missing[*]}; rerun deckctl apply"
else
  module_json READY "Flatseal and Zen Browser installed"
fi
