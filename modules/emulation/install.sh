#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="$DECKCTL_ROOT/lib${PYTHONPATH:+:$PYTHONPATH}"
if python3 -m deckctl.setup_cleanup emudeck-ready; then
  echo "EmuDeck manager and vendor setup completion verified; installer staging skipped."
  exit 0
fi
stage="$HOME/Desktop/Deck-Setup-Staged"; mkdir -p "$stage"
if ! command -v curl >/dev/null 2>&1; then echo "curl is required to stage EmuDeck" >&2; exit 1; fi
if command -v curl >/dev/null 2>&1; then
  curl -fL --retry 2 https://www.emudeck.com/EmuDeck.desktop -o "$stage/EmuDeck.desktop" || exit 1
  chmod +x "$stage/EmuDeck.desktop"
fi
cat > "$stage/README-EMUDECK.txt" <<'EOF'
Run EmuDeck.desktop interactively. Choose DECK-EMU for the Emulation tree if using split storage. Import your legally obtained BIOS/firmware from private storage and run EmuDeck's BIOS checker. Use ES-DE for the full library and Steam ROM Manager for favorites/current titles.
EOF

python3 -m deckctl.setup_cleanup record emudeck
