#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
loader="$HOME/homebrew/services/PluginLoader"
enabled=""
if command -v systemctl >/dev/null 2>&1; then
  enabled="$(systemctl is-enabled plugin_loader.service 2>/dev/null || true)"
fi
if [[ -x "$loader" || "$enabled" == "enabled" ]]; then
  module_json CONFIG_REQUIRED "Decky installed; audit curated plugins with 'deckctl decky plugins'"
else
  module_json CONFIG_REQUIRED "Decky stable installer staged; interactive install required"
fi
