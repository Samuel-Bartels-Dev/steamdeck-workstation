#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
img="$HOME/Android_Waydroid/waydroid.img"
state1="$HOME/.local/share/waydroid"
state2="$HOME/waydroid"
if [[ -f "$img" && ( -d "$state1" || -d "$state2" ) ]]; then
  module_json READY "Waydroid image and Android user state found"
elif [[ -f "$img" ]]; then
  module_json CONFIG_REQUIRED "Waydroid image exists but first launch is pending; run: deckctl android retry"
else
  module_json CONFIG_REQUIRED "Waydroid is not installed; run: deckctl android install and choose Android 13 with Google Play"
fi
