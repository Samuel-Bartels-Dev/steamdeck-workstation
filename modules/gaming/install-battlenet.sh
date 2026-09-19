#!/usr/bin/env bash
set -euo pipefail

# NonSteamLaunchers officially supports launcher names as command-line arguments.
# This deliberately installs Battle.net only and bypasses NSL's full launcher picker.
NSL_URL="https://raw.githubusercontent.com/moraroy/NonSteamLaunchers-On-Steam-Deck/main/NonSteamLaunchers.sh"
CACHE_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/deckctl/nonsteamlaunchers"
SCRIPT="$CACHE_DIR/NonSteamLaunchers.sh"
RECEIPT="${XDG_STATE_HOME:-$HOME/.local/state}/deckctl/nsl-battlenet-source.txt"

mkdir -p "$CACHE_DIR" "$(dirname "$RECEIPT")"

if ! command -v curl >/dev/null 2>&1; then
  echo "ERROR: curl is required for the Battle.net installer." >&2
  exit 2
fi

echo "Downloading current NonSteamLaunchers installer from the official project..."
curl -fL --retry 3 --connect-timeout 15 "$NSL_URL" -o "$SCRIPT.tmp"
test -s "$SCRIPT.tmp"
mv "$SCRIPT.tmp" "$SCRIPT"
chmod 0700 "$SCRIPT"

{
  echo "source=$NSL_URL"
  echo "launcher=Battle.net"
  if command -v sha256sum >/dev/null 2>&1; then
    printf 'sha256='; sha256sum "$SCRIPT" | awk '{print $1}'
  fi
  date -u '+downloaded_at=%Y-%m-%dT%H:%M:%SZ'
} > "$RECEIPT"

cat <<'EOF'

Installing Battle.net only through NonSteamLaunchers.
The full NSL launcher-selection menu is intentionally bypassed.
Battle.net's own installer/login windows may still appear; complete those normally.

EOF

# The upstream script consumes launcher names from "$@". Keep default shared-prefix
# behavior unless the user intentionally chooses a different NSL workflow later.
/bin/bash "$SCRIPT" "Battle.net"
