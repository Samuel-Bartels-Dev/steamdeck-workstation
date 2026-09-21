#!/usr/bin/env bash
set -euo pipefail
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
desktop_app_install com.parsecgaming.parsec
if component_selected remote moonlight; then flatpak_install com.moonlight_stream.Moonlight; fi
if component_selected remote chiaki; then flatpak_install io.github.streetpea.Chiaki4deck; fi
if component_selected remote tailscale; then
stage="$HOME/Desktop/Deck-Setup-Staged"; mkdir -p "$stage"

helper="$DECKCTL_ROOT/modules/remote/install-tailscale-steamos.sh"
cat > "$stage/Install-Tailscale.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Install Tailscale for Steam Deck
Comment=Install the SteamOS-specific Tailscale service and authenticate this Deck
Exec=konsole -e bash -lc '"$helper"; exec bash'
Icon=network-vpn
Terminal=false
StartupNotify=true
EOF
chmod +x "$stage/Install-Tailscale.desktop"

cat > "$stage/README-REMOTE.txt" <<'EOF'
Tailscale: launch Install-Tailscale.desktop. It fetches the maintained tailscale-dev/deck-tailscale installer, installs the persistent service, and prompts for QR authentication. Do not install Tailscale from Discover or pacman.
Moonlight: pair each Sunshine host.
chiaki-ng: register PlayStation locally, then test PSN remote play from a non-home network.
EOF

PYTHONPATH="$DECKCTL_ROOT/lib${PYTHONPATH:+:$PYTHONPATH}" python3 -m deckctl.setup_cleanup record tailscale

fi
