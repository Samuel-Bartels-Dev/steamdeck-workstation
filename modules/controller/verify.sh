#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
steam="$HOME/.local/share/Steam"
[[ -d "$steam" ]] || { module_json CONFIG_REQUIRED "Steam user data not initialized yet"; exit 0; }
module_json READY "Controller profile manager ready"
