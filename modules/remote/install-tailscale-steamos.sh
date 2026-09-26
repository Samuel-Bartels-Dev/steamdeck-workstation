#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/tailscale-dev/deck-tailscale.git"
ARCHIVE_URL="https://github.com/tailscale-dev/deck-tailscale/archive/refs/heads/main.tar.gz"
WORK_DIR="$HOME/deck-tailscale"

# An installed and connected client does not need another vendor download/login.
TS_EXISTING="$(command -v tailscale 2>/dev/null || true)"
if [ -z "$TS_EXISTING" ] && [ -x /opt/tailscale/tailscale ]; then TS_EXISTING=/opt/tailscale/tailscale; fi
if [ -n "$TS_EXISTING" ] && "$TS_EXISTING" status --json | python3 -c '
import json, sys
try:
    state = json.load(sys.stdin)
except (ValueError, OSError):
    sys.exit(1)
if not isinstance(state, dict) or state.get("BackendState") != "Running": sys.exit(1)
print("Tailscale is connected. Existing installation reused; no download or login needed.")
if state.get("Health"): print("Tailscale reports health warnings. Run tailscale status to review them; installation success does not prove DNS health.")
'; then exit 0; fi

printf '\n=== Tailscale for Steam Deck ===\n\n'
printf 'This uses the SteamOS-specific tailscale-dev/deck-tailscale installer.\n'
printf 'It does NOT install Tailscale from Discover/Flatpak or pacman.\n\n'

# Download into a separate tree; a failed refresh must not remove local files.
if command -v git >/dev/null 2>&1 && [ -d "$WORK_DIR/.git" ]; then
  printf 'Updating existing deck-tailscale checkout...\n'
  git -C "$WORK_DIR" pull --ff-only
else
  stage="$(mktemp -d "$HOME/.deck-tailscale-stage.XXXXXX")"
  trap 'rm -rf "$stage"' EXIT
  if command -v git >/dev/null 2>&1; then
    git clone --depth 1 "$REPO_URL" "$stage/repo"
  else
    curl -fL --retry 3 --connect-timeout 15 "$ARCHIVE_URL" -o "$stage/source.tar.gz"
    mkdir "$stage/repo"
    tar -xzf "$stage/source.tar.gz" --strip-components=1 -C "$stage/repo"
  fi
  test -f "$stage/repo/tailscale.sh" || { echo 'Upstream installer missing' >&2; exit 1; }
  if [ -e "$WORK_DIR" ] || [ -L "$WORK_DIR" ]; then
    backup="$(mktemp -d "$HOME/deck-tailscale-backup.XXXXXX")"
    mv "$WORK_DIR" "$backup/original"
    printf 'Previous installer preserved at %s\n' "$backup/original"
  fi
  mv "$stage/repo" "$WORK_DIR"
fi

cd "$WORK_DIR"

printf '\nThe installer needs sudo because tailscaled is a system service.\n'
printf 'Enter the Steam Deck sudo password when prompted.\n\n'
sudo -v
sudo bash tailscale.sh

# The upstream installer creates this profile fragment. Source it for this shell.
if [ -r /etc/profile.d/tailscale.sh ]; then
  # shellcheck disable=SC1091
  source /etc/profile.d/tailscale.sh
fi

TS_BIN="$(command -v tailscale 2>/dev/null || true)"
if [ -z "$TS_BIN" ]; then
  for candidate in /opt/tailscale/tailscale /usr/bin/tailscale; do
    if [ -x "$candidate" ]; then TS_BIN="$candidate"; break; fi
  done
fi

if [ -z "$TS_BIN" ]; then
  printf '\nERROR: Tailscale installer completed but the CLI was not found.\n' >&2
  printf 'Re-run this helper or inspect: %s\n' "$WORK_DIR" >&2
  exit 1
fi

printf '\nTailscale installed. Next you will get a QR/login URL.\n'
printf 'Authenticate it to your PERSONAL tailnet.\n\n'
sudo "$TS_BIN" up --qr --operator=deck --ssh

printf '\nCurrent Tailscale status:\n'
"$TS_BIN" status || sudo "$TS_BIN" status || true

printf '\nTailscale setup complete. It should start automatically on boot.\n'
printf 'Press Enter to close this window.\n'
read -r _
