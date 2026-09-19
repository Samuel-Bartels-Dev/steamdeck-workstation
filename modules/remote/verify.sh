#!/usr/bin/env bash
set -euo pipefail
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
if ! flatpak info com.moonlight_stream.Moonlight >/dev/null 2>&1 || ! flatpak info io.github.streetpea.Chiaki4deck >/dev/null 2>&1; then
  module_json DEGRADED "Moonlight and/or chiaki-ng missing"
  exit 0
fi

ts=""
if command -v tailscale >/dev/null 2>&1; then
  ts="$(command -v tailscale)"
elif [ -x /opt/tailscale/tailscale ]; then
  ts="/opt/tailscale/tailscale"
elif [ -x /usr/bin/tailscale ]; then
  ts="/usr/bin/tailscale"
fi

if [ -z "$ts" ]; then
  module_json CONFIG_REQUIRED "Moonlight/chiaki-ng installed; run the staged SteamOS-specific Tailscale installer"
else
  if "$ts" status >/dev/null 2>&1 || sudo -n "$ts" status >/dev/null 2>&1; then
    module_json CONFIG_REQUIRED "Tailscale installed/connected; pair Sunshine/PlayStation and test away-network paths"
  else
    module_json CONFIG_REQUIRED "Tailscale installed but not authenticated/connected; run tailscale up or resume guided setup"
  fi
fi
