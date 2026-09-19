#!/usr/bin/env bash
set -euo pipefail
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
app_status=0
for app in org.videolan.VLC tv.plex.PlexDesktop com.spotify.Client; do
  desktop_app_install "$app" || app_status=1
done
stage="$HOME/Desktop/Deck-Setup-Staged"
helper="$HOME/.local/share/deckctl/media"
mkdir -p "$stage" "$helper"
cp "$DECKCTL_ROOT/modules/media/services.json" "$helper/services.json"
cp "$DECKCTL_ROOT/modules/media/setup-media.sh" "$helper/setup-media.sh"
chmod +x "$helper/setup-media.sh"
cat > "$stage/Media-Apps.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Set Up Streaming Media Apps
Comment=Create Netflix, Hulu, Crunchyroll and Prime Video Game Mode shortcuts
Exec=konsole -e $helper/setup-media.sh --all
Icon=video-display
Terminal=false
StartupNotify=true
DESKTOP
chmod +x "$stage/Media-Apps.desktop"
echo "Optional media-app setup staged: $stage/Media-Apps.desktop"

PYTHONPATH="$DECKCTL_ROOT/lib" python3 -c 'from deckctl.desktop import apply; raise SystemExit(apply())'
exit "$app_status"
