#!/usr/bin/env bash
set -euo pipefail
PYTHONPATH="$DECKCTL_ROOT/lib" python3 -c 'from deckctl.workspace import setup; raise SystemExit(setup())'
