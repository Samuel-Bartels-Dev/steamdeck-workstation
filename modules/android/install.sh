#!/usr/bin/env bash
set -euo pipefail
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
stage="$HOME/Desktop/Deck-Setup-Staged"
helper="$HOME/.local/share/deckctl/android"
mkdir -p "$stage" "$helper"
cat > "$helper/waydroid-setup.sh" <<'HELPER'
#!/usr/bin/env bash
set -euo pipefail
# Use the same protected install/repair/first-launch flow as guided provisioning.
control="$HOME/.local/share/steamdeck-workstation/current/bin/deckctl"
if [[ -x "$control" ]]; then
  exec "$control" android retry
fi
if command -v deckctl >/dev/null 2>&1; then
  exec deckctl android retry
fi
echo "deckctl is unavailable. Run the normal project install.sh to restore the control plane." >&2
exit 1
HELPER
chmod +x "$helper/waydroid-setup.sh"
cat > "$stage/Waydroid-Android.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Install or Repair Android (Waydroid)
Comment=SteamOS-aware Waydroid setup for Android gaming
Exec=konsole -e $helper/waydroid-setup.sh
Icon=applications-games
Terminal=false
StartupNotify=true
EOF
chmod +x "$stage/Waydroid-Android.desktop"
echo "Android/Waydroid guided installer staged: $stage/Waydroid-Android.desktop"

PYTHONPATH="$DECKCTL_ROOT/lib${PYTHONPATH:+:$PYTHONPATH}" python3 -m deckctl.setup_cleanup record android
