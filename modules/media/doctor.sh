#!/usr/bin/env bash
set -euo pipefail
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
stage="$HOME/Desktop/Deck-Setup-Staged/Media-Apps.desktop"
if [[ -f "$stage" ]]; then
  echo "Re-run the optional media setup from: $stage"
  if command -v xdg-open >/dev/null 2>&1; then xdg-open "$stage" >/dev/null 2>&1 || true; fi
else
  echo "Media setup helper is not staged. Run: ./bin/deckctl apply"
fi
