#!/usr/bin/env bash
set -euo pipefail
if command -v flatpak >/dev/null 2>&1; then
  flatpak install -y --user flathub com.github.tchx84.Flatseal || true
fi
