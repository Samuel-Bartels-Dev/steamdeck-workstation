#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
model="$($DECKCTL_ROOT/bin/deckctl detect | python3 -c 'import json,sys;print(json.load(sys.stdin)["model"])')"
case "$model" in oled|lcd) module_json READY "Steam Deck $model detected";; *) module_json DEGRADED "Steam Deck model not detected (safe for repo testing only)";; esac
