#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$HOME/DeckBackups"
"$DECKCTL_ROOT/bin/deckctl" backup saves
