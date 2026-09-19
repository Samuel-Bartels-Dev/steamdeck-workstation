#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
[[ -d "$HOME/DeckBackups" ]] && module_json READY "Local backup destination exists" || module_json NOT_INSTALLED "~/DeckBackups missing"
