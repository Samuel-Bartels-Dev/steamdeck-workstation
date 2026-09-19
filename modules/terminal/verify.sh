#!/usr/bin/env bash
set -euo pipefail
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
result="$("$DECKCTL_ROOT/bin/deckctl" terminal status --json 2>/dev/null || true)"
status="$(printf '%s' "$result" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("status","FAILED"))' 2>/dev/null || echo FAILED)"
message="$(printf '%s' "$result" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("message","Terminal status unavailable"))' 2>/dev/null || echo 'Terminal status unavailable')"
module_json "$status" "$message"
