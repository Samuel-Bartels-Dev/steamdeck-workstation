#!/usr/bin/env bash
set -euo pipefail

helper="$HOME/.local/share/deckctl/media"
services="$helper/services.json"
appdir="$HOME/.local/share/applications"
bindir="$helper/bin"
submitted="$helper/submitted"
mkdir -p "$appdir" "$bindir" "$submitted"

if [[ ! -f "$services" ]]; then
  echo "Missing service registry: $services" >&2
  exit 1
fi

mode="interactive"
if [[ "${1:-}" == "--all" ]]; then mode="all"; fi

printf '\nSteam Deck Media Apps\n'
printf '%s\n' '---------------------'
printf '%s\n' 'Creates Netflix, Hulu, Crunchyroll, and Prime Video as single-site Chrome kiosk shortcuts in Steam Game Mode.'
printf '%s\n\n' 'Media sessions use Chrome --kiosk with the normal persistent Chrome profile. KeeperFill can still inject into the page when installed/unlocked; deckctl never stores credentials.'

python3 - "$services" <<'PYMEDIA' > "$helper/service-lines.tsv"
import json,sys,os
from pathlib import Path
path=Path(os.environ.get('DECKCTL_CONFIG',str(Path.home()/'.config/deckctl')))/'components.json'
choices=json.loads(path.read_text()).get('media') if path.exists() else None
for sid,data in json.load(open(sys.argv[1])).items():
    if choices is None or sid in choices:
        print(f"{sid}\t{data['name']}\t{data['url']}\t{'Y' if data.get('default',False) else 'N'}")
PYMEDIA
if [[ ! -s "$helper/service-lines.tsv" ]]; then
  echo "No media web shortcuts selected."
  exit 0
fi

if ! flatpak info com.google.Chrome >/dev/null 2>&1; then
  echo "Installing Google Chrome Flatpak..."
  flatpak install --user -y flathub com.google.Chrome
fi

# Let Chrome see input devices used by Steam Deck/browser web apps. User-level only.
flatpak override --user --filesystem=/run/udev:ro com.google.Chrome >/dev/null 2>&1 || true


steam_has_name() {
  local name="$1"
  local vdf
  while IFS= read -r -d '' vdf; do
    if grep -aFq "$name" "$vdf" 2>/dev/null; then
      return 0
    fi
  done < <(find "$HOME/.local/share/Steam/userdata" -type f -path '*/config/shortcuts.vdf' -print0 2>/dev/null)
  return 1
}

steam_add() {
  local desktop="$1"
  if command -v steamos-add-to-steam >/dev/null 2>&1; then
    if steamos-add-to-steam "$desktop"; then
      return 0
    fi
    echo "[warn] steamos-add-to-steam failed for $desktop; trying Steam URI fallback."
  fi

  if command -v steam >/dev/null 2>&1; then
    local encoded
    encoded="$(python3 - "$desktop" <<'PY'
import sys,urllib.parse,os
print(urllib.parse.quote(os.path.realpath(sys.argv[1]), safe=''))
PY
)"
    touch /tmp/addnonsteamgamefile 2>/dev/null || true
    steam "steam://addnonsteamgame/$encoded" >/dev/null 2>&1 &
    sleep 2
    return 0
  fi

  return 1
}

selected=0
submitted_now=0
pending=0
ready=0
while IFS=$'\t' read -r sid name url default; do
  choose="Y"
  if [[ "$mode" != "all" ]]; then
    prompt="Add $name to Steam Game Mode? [$default/$( [[ "$default" == "Y" ]] && echo n || echo y )] "
    read -r -p "$prompt" ans || ans=""
    [[ -z "$ans" ]] && ans="$default"
    [[ "$ans" =~ ^[Yy]$ ]] || choose="N"
  fi
  [[ "$choose" == "Y" ]] || continue

  selected=$((selected+1))
  runner="$bindir/$sid"
  desktop="$appdir/deck-media-$sid.desktop"

  cat > "$runner" <<RUNNEREOF
#!/usr/bin/env bash
exec flatpak run com.google.Chrome \
  --no-first-run \
  --disable-session-crashed-bubble \
  --kiosk \
  "$url"
RUNNEREOF
  chmod +x "$runner"

  cat > "$desktop" <<DESKTOPEOF
[Desktop Entry]
Type=Application
Name=$name
Comment=$name streaming shortcut for Steam Game Mode
Exec=$runner
Icon=web-browser
Terminal=false
Categories=AudioVideo;Video;
StartupNotify=true
DESKTOPEOF
  chmod +x "$desktop"
  control_root="${DECKCTL_ROOT:-$HOME/.local/share/steamdeck-workstation/current}"
  PYTHONPATH="$control_root/lib" python3 -c 'from deckctl.desktop import apply; raise SystemExit(apply())'

  if steam_has_name "$name"; then
    echo "[ready] $name is already present in Steam shortcuts"
    : > "$submitted/$sid"
    ready=$((ready+1))
  elif [[ -f "$submitted/$sid" ]]; then
    echo "[pending] $name was already submitted to Steam; waiting for Steam refresh instead of submitting it again"
    pending=$((pending+1))
  else
    echo "Submitting $name to Steam Game Mode..."
    if steam_add "$desktop"; then
      : > "$submitted/$sid"
      submitted_now=$((submitted_now+1))
    else
      echo "[warn] Could not submit $name to Steam automatically."
      echo "       Desktop entry is ready at: $desktop"
    fi
  fi
done < "$helper/service-lines.tsv"

rm -f "$helper/service-lines.tsv"

printf '\nConfigured %d media app(s): %d ready, %d submitted now, %d pending Steam refresh.\n' "$selected" "$ready" "$submitted_now" "$pending"
printf '%s\n' 'Desktop provisioning is complete. A shortcut may remain PENDING until Steam refreshes; do not rerun this step just because shortcuts.vdf has not updated yet.'
printf '%s\n' 'Return to Game Mode after this setup pass. Steam will refresh during the session switch.'
printf '%s\n' 'Launch each tile there and sign in normally. KeeperFill can autofill matching records inside kiosk mode when the extension is installed and the vault is unlocked.'
printf '%s\n' 'Recommended controls: right trackpad=mouse, trackpad click/R2=left click, left trackpad=scroll, touchscreen enabled.'
printf '%s\n' 'Use Decky SteamGridDB afterward for polished cover/hero/logo artwork.'
