#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
case "${1:-}" in
  --help|-h)
    echo 'Usage: tests/run-tests.sh [--unit|--regression|--integration]'
    echo 'Default/--regression runs isolated repository contracts. --integration runs the isolated UI test.'
    echo 'Real container tests are MODIFIES_STATE and must be invoked explicitly outside this harness.'
    ;;
  --unit) python3 "$ROOT/tests/contract/test_production.py" ;;
  --integration) python3 "$ROOT/tests/integration/test_setup_ui.py" ;;
  --regression|'') "$ROOT/bin/deckctl" repo validate ;;
  *) echo 'Unknown test mode. Use --help.' >&2; exit 2 ;;
esac
