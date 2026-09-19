#!/usr/bin/env bash
set -euo pipefail
source "$DECKCTL_ROOT/lib/deckctl/module.sh"

printf 'Development doctor\n'
printf '%s\n' '------------------'

if command -v codex >/dev/null 2>&1; then
  echo "Codex: $(codex --version 2>/dev/null | head -n1 || echo present-but-broken)"
  codex login status 2>&1 || true
elif [[ -x "$HOME/.local/bin/codex" ]]; then
  echo "Codex: $($HOME/.local/bin/codex --version 2>/dev/null | head -n1 || echo present-but-broken)"
  "$HOME/.local/bin/codex" login status 2>&1 || true
else
  echo "Codex: MISSING"
  echo "Repair: $DECKCTL_ROOT/modules/dev/install-codex.sh"
fi

if have distrobox; then echo "Distrobox: $(distrobox --version 2>/dev/null | head -n1)"; else echo "Distrobox: MISSING from PATH"; fi
if have podman; then echo "Podman: $(podman --version 2>/dev/null | head -n1)"; else echo "Podman: MISSING from PATH"; fi
if have distrobox && have podman; then distrobox list 2>/dev/null || true; fi
