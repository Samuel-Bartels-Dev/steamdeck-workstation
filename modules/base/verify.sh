#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
if ! have flatpak; then module_json FAILED "Flatpak missing"; exit 0; fi
if ! flatpak remotes --user --columns=name 2>/dev/null | grep -qx flathub; then module_json NOT_INSTALLED "Flathub user remote not configured"; exit 0; fi
module_json READY "Flatpak + Flathub available"
