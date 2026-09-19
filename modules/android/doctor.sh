#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
repo="$HOME/steamos-waydroid-bundle"
img="$HOME/Android_Waydroid/waydroid.img"
if [[ -f "$img" ]]; then
  echo "Android image exists: $img"
  echo "If first-run user state is missing, deckctl android retry opens the bundled launcher."
  if [[ -x "$repo/steamos-waydroid-installer.sh" ]]; then
    echo "For normal SteamOS host repair, run in Desktop Mode:"
    echo "  deckctl android repair"
    echo "The upstream installer auto-selects protected repair when the Android image already exists."
  else
    echo "Installer checkout is missing. Re-run: deckctl apply, then deckctl setup run"
  fi
else
  echo "No persistent Waydroid Android image detected."
  echo "Run: deckctl apply && deckctl setup run"
fi
