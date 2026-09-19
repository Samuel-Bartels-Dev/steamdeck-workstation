#!/usr/bin/env bash
PYTHONPATH="$DECKCTL_ROOT/lib" python3 -c 'from deckctl.workspace import verify; raise SystemExit(verify())'
