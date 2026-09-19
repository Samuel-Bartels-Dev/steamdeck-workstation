#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
if [[ -d "$HOME/.local/share/Steam/userdata" ]]; then
  module_json READY "Steam library audit available"
else
  module_json CONFIG_REQUIRED "Steam userdata not initialized"
fi
