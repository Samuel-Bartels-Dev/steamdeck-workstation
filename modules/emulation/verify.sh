#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
if [[ -d "$HOME/Emulation" ]] || find /run/media -maxdepth 3 -type d -name Emulation -print -quit 2>/dev/null | grep -q .; then module_json CONFIG_REQUIRED "Emulation tree found; validate BIOS/firmware and ROMs"; else module_json CONFIG_REQUIRED "EmuDeck installer staged; first-run wizard required"; fi
