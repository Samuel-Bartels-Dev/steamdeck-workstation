#!/usr/bin/env bash
set -euo pipefail
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
launcher_selected() { PYTHONPATH="$DECKCTL_ROOT/lib" python3 -m deckctl.gaming_options "$1"; }
if launcher_selected heroic; then flatpak_install com.heroicgameslauncher.hgl; fi
if launcher_selected protonplus; then flatpak_install com.vysp3r.ProtonPlus; fi
stage="$HOME/Desktop/Deck-Setup-Staged"; mkdir -p "$stage"
if launcher_selected nonsteamlaunchers && have curl; then curl -fL --retry 2 https://raw.githubusercontent.com/moraroy/NonSteamLaunchers-On-Steam-Deck/main/NonSteamLaunchers.desktop -o "$stage/NonSteamLaunchers.desktop" || true; chmod +x "$stage/NonSteamLaunchers.desktop" 2>/dev/null || true; fi
cat > "$stage/README-GAMING.txt" <<'EOF'
Heroic: sign in and enable Add games to Steam automatically.
Battle.net: guided setup uses the targeted `deckctl launcher install battlenet` path and does NOT open the full NSL launcher picker.
NonSteamLaunchers.desktop is staged only as an advanced/manual fallback for other launchers.
Use Steam Game Mode as the normal launch surface afterward.
EOF
