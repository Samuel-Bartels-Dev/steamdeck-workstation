#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"

desktop_app_satisfied com.visualstudio.code || { module_json NOT_INSTALLED "VS Code Flatpak missing"; exit 0; }
desktop_app_satisfied dev.zed.Zed || { module_json NOT_INSTALLED "Zed Flatpak missing; rerun deckctl apply"; exit 0; }

if component_selected dev codex; then
codex_cmd=""
if command -v codex >/dev/null 2>&1; then codex_cmd="$(command -v codex)"
elif [[ -x "$HOME/.local/bin/codex" ]]; then codex_cmd="$HOME/.local/bin/codex"
elif [[ -x "$HOME/.codex/bin/codex" ]]; then codex_cmd="$HOME/.codex/bin/codex"
fi

if [[ -z "$codex_cmd" ]] || ! "$codex_cmd" --version >/dev/null 2>&1; then
  module_json DEGRADED "Selected editors satisfied; Codex CLI is missing or not runnable"
  exit 0
fi

login="not logged in"
if "$codex_cmd" login status 2>&1 | grep -qi 'Logged in'; then login="logged in"; fi

if [[ "$login" != "logged in" ]]; then
  module_json CONFIG_REQUIRED "Codex CLI installed; run codex login"
  exit 0
fi
fi
if component_selected dev claude-code; then
  if [[ ! -x "$HOME/.local/bin/claude" ]] || ! "$HOME/.local/bin/claude" --version >/dev/null 2>&1; then
    module_json DEGRADED "Claude Code is missing or not runnable; rerun deckctl apply"
    exit 0
  fi
  if ! "$HOME/.local/bin/claude" auth status >/dev/null 2>&1; then
    module_json CONFIG_REQUIRED "Claude Code installed; run claude to sign in"
    exit 0
  fi
fi
if component_selected dev distrobox; then
  if ! have distrobox || ! have podman || ! distrobox list 2>/dev/null | grep -Eq '(^|[[:space:]])deck-dev([[:space:]]|$)'; then
    module_json DEGRADED "Selected development container is not ready"
    exit 0
  fi
fi
if component_selected dev docker; then
  if ! "$DECKCTL_ROOT/bin/deckctl" containers status >/dev/null 2>&1; then
    module_json CONFIG_REQUIRED "Selected Docker engine needs setup or a live container test; run deckctl containers status"
    exit 0
  fi
fi
module_json READY "Selected development tools are ready"
