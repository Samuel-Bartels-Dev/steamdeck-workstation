#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$DECKCTL_CONFIG"
"$DECKCTL_ROOT/bin/deckctl" storage health || true
