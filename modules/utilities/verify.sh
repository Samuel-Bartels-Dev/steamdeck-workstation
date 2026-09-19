#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
if flatpak info com.github.tchx84.Flatseal >/dev/null 2>&1; then
  module_json READY "Flatseal available for Flatpak permission recovery"
else
  module_json NOT_INSTALLED "Flatseal missing"
fi
