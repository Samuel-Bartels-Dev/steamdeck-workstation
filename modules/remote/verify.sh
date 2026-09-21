#!/usr/bin/env bash
set -euo pipefail
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
if ! desktop_app_satisfied com.parsecgaming.parsec; then
  module_json NOT_INSTALLED "Selected Parsec client is missing; rerun deckctl apply"; exit 0
fi
if component_selected remote moonlight && ! flatpak_has com.moonlight_stream.Moonlight; then
  module_json NOT_INSTALLED "Selected Moonlight client is missing"; exit 0
fi
if component_selected remote chiaki && ! flatpak_has io.github.streetpea.Chiaki4deck; then
  module_json NOT_INSTALLED "Selected chiaki-ng client is missing"; exit 0
fi
if ! component_selected remote tailscale; then
  module_json READY "Selected remote clients are installed; pairing is handled in guided setup"; exit 0
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
