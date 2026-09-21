#!/usr/bin/env bash
set -euo pipefail
"$DECKCTL_ROOT/bin/deckctl" terminal apply
"$DECKCTL_ROOT/bin/deckctl" ai-workspace install
