#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
missing=()
desktop_app_satisfied com.github.tchx84.Flatseal || missing+=("Flatseal")
desktop_app_satisfied app.zen_browser.zen || missing+=("Zen Browser")
if (( ${#missing[@]} )); then
  module_json NOT_INSTALLED "Missing desktop apps: ${missing[*]}; rerun deckctl apply"
else
  module_json READY "Selected utility apps satisfied"
fi
