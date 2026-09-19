#!/usr/bin/env bash
set -euo pipefail
stage="$HOME/Desktop/Deck-Setup-Staged"; mkdir -p "$stage"

# Stage Decky's official installer. Guided setup launches this only when the
# actual PluginLoader/service detector says Decky is missing.
if command -v curl >/dev/null 2>&1; then
  if curl -fL --retry 2 https://github.com/SteamDeckHomebrew/decky-installer/releases/latest/download/decky_installer.desktop -o "$stage/decky_installer.desktop"; then
    PYTHONPATH="$DECKCTL_ROOT/lib${PYTHONPATH:+:$PYTHONPATH}" python3 -m deckctl.setup_cleanup record decky
  fi
  chmod +x "$stage/decky_installer.desktop" 2>/dev/null || true
fi

# Clean legacy checklist artifacts from old releases. Desired state is stored
# in ~/.config/deckctl/decky-selection.json; text files are never install state.
rm -f "$HOME/Desktop/Decky Selected Plugins.txt" "$stage/DECKY-PLUGINS.txt"

echo "Decky official installer staged at $stage/decky_installer.desktop"
echo "Guided setup will: verify Decky Loader -> select desired plugins -> install selected trusted Store artifacts -> verify actual plugin folders."
