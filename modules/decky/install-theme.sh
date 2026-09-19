#!/usr/bin/env bash
set -euo pipefail
ROOT="${DECKCTL_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
exec "$ROOT/bin/deckctl" decky css apply
