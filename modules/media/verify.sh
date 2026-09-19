#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
missing=()
desktop_app_satisfied org.videolan.VLC || missing+=("VLC")
desktop_app_satisfied tv.plex.PlexDesktop || missing+=("Plex")
desktop_app_satisfied com.spotify.Client || missing+=("Spotify")
if (( ${#missing[@]} )); then
  module_json NOT_INSTALLED "Missing desktop apps: ${missing[*]}; rerun deckctl apply"
  exit 0
fi
appdir="$HOME/.local/share/applications"
chrome=false
flatpak_has com.google.Chrome && chrome=true

names=("Netflix" "Hulu" "Crunchyroll" "Prime Video")
ids=("netflix" "hulu" "crunchyroll" "prime-video")
created=0
steam_seen=0
for i in "${!ids[@]}"; do
  [[ -f "$appdir/deck-media-${ids[$i]}.desktop" ]] && created=$((created+1))
done

# Non-Steam shortcuts live in a binary VDF, but shortcut names are stored as plain strings.
while IFS= read -r -d '' vdf; do
  for name in "${names[@]}"; do
    if grep -aFq "$name" "$vdf" 2>/dev/null; then steam_seen=$((steam_seen+1)); fi
  done
done < <(find "$HOME/.local/share/Steam/userdata" -type f -path '*/config/shortcuts.vdf' -print0 2>/dev/null)
# A service name may appear in multiple VDFs; cap for reporting.
(( steam_seen > 4 )) && steam_seen=4

if [[ "$created" -eq 4 && "$steam_seen" -eq 4 && "$chrome" == true ]]; then
  module_json READY "Selected media apps satisfied; 4 media web apps present in Steam shortcuts"
elif [[ "$created" -eq 4 && "$chrome" == true ]]; then
  module_json DEGRADED "4 media launchers created, but only $steam_seen/4 are detected in Steam; rerun deckctl media setup in Desktop Mode"
elif [[ "$created" -gt 0 ]]; then
  module_json DEGRADED "$created/4 media launchers created; rerun deckctl media setup"
else
  module_json READY "Selected media apps satisfied; optional media web apps are not configured"
fi
