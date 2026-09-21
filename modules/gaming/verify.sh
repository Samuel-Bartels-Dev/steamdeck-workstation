#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
launcher_selected() { PYTHONPATH="$DECKCTL_ROOT/lib" python3 -m deckctl.gaming_options "$1"; }
miss=()
if launcher_selected heroic; then flatpak_has com.heroicgameslauncher.hgl || miss+=(Heroic); fi
if launcher_selected protonplus; then flatpak_has com.vysp3r.ProtonPlus || miss+=(ProtonPlus); fi
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
if launcher_selected battlenet && (( ! battle )); then
  module_json CONFIG_REQUIRED "Selected Battle.net launcher pending; run guided setup"
elif launcher_selected heroic || launcher_selected battlenet; then
  module_json CONFIG_REQUIRED "Selected launchers installed; account sign-in and game configuration may require user action"
elif launcher_selected nonsteamlaunchers && [[ ! -f "$HOME/Desktop/Deck-Setup-Staged/NonSteamLaunchers.desktop" ]]; then
  module_json NOT_INSTALLED "Selected NonSteamLaunchers helper is not staged"
else
  module_json READY "Selected gaming tools are available; unselected launchers are optional"
fi
