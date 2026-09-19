#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$HOME/.config/deckctl/controller-layouts"
"$DECKCTL_ROOT/bin/deckctl" controller status
