#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
miss=()
flatpak_has com.heroicgameslauncher.hgl || miss+=(Heroic)
flatpak_has com.vysp3r.ProtonPlus || miss+=(ProtonPlus)
if ((${#miss[@]})); then
  module_json NOT_INSTALLED "Missing: ${miss[*]}"
  exit 0
fi
battle=0
base="$HOME/.local/share/Steam/steamapps/compatdata"
for prefix in NonSteamLaunchers 'Battle.netLauncher'; do
  for exe in 'Battle.net Launcher.exe' 'Battle.net.exe'; do
    [[ -f "$base/$prefix/pfx/drive_c/Program Files (x86)/Battle.net/$exe" ]] && battle=1
  done
done
if (( battle )); then
  module_json CONFIG_REQUIRED "Heroic/ProtonPlus/Battle.net installed; account/game-specific sign-in or Steam integration may still require user action"
else
  module_json CONFIG_REQUIRED "Heroic/ProtonPlus installed; Battle.net pending (guided setup uses targeted NSL Battle.net install)"
fi
