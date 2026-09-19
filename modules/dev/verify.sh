#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"

flatpak_has com.visualstudio.code || { module_json NOT_INSTALLED "VS Code Flatpak missing"; exit 0; }

codex_cmd=""
if command -v codex >/dev/null 2>&1; then codex_cmd="$(command -v codex)"
elif [[ -x "$HOME/.local/bin/codex" ]]; then codex_cmd="$HOME/.local/bin/codex"
elif [[ -x "$HOME/.codex/bin/codex" ]]; then codex_cmd="$HOME/.codex/bin/codex"
fi

if [[ -z "$codex_cmd" ]] || ! "$codex_cmd" --version >/dev/null 2>&1; then
  module_json DEGRADED "VS Code installed; Codex CLI is missing or not runnable"
  exit 0
fi

login="not logged in"
if "$codex_cmd" login status 2>&1 | grep -qi 'Logged in'; then login="logged in"; fi

box="missing"
if have distrobox && have podman && distrobox list 2>/dev/null | grep -Eq '(^|[[:space:]])deck-dev([[:space:]]|$)'; then box="ready"; fi

if [[ "$login" == "logged in" && "$box" == "ready" ]]; then
  module_json READY "Codex CLI installed/authenticated; deck-dev ready"
elif [[ "$login" != "logged in" ]]; then
  module_json CONFIG_REQUIRED "Codex CLI installed but ChatGPT authentication is incomplete; run: codex login"
else
  module_json DEGRADED "Codex installed/authenticated; deck-dev is not ready (Distrobox/Podman path needs repair)"
fi
