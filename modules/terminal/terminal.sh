# Managed by steamdeck-workstation terminal module. Bash interactive shell only.
case ":$PATH:" in
  *":$HOME/.local/bin:"*) ;;
  *) export PATH="$HOME/.local/bin:$PATH" ;;
esac

export STARSHIP_CONFIG="$HOME/.config/deckctl/terminal/starship.toml"
export POSH_THEME="$HOME/.config/deckctl/terminal/bubble-gum-rave.omp.json"
export FZF_DEFAULT_OPTS="--height=45% --layout=reverse --border=rounded --info=inline --prompt='❯ ' --pointer='◆' --marker='✓' --color=bg+:#241332,bg:#090612,spinner:#42f5ff,hl:#ff4fd8,fg:#f8e7ff,header:#a970ff,info:#b9ff63,pointer:#42f5ff,marker:#ff4fd8,fg+:#ffffff,prompt:#a970ff,hl+:#ff2fb3,border:#a970ff"

_deckctl_tool_selected() {
  local choices="$HOME/.config/deckctl/terminal/selected-tools"
  [[ ! -f "$choices" ]] || grep -Fxq "$1" "$choices"
}

# Keep all decoration out of non-interactive scripts.
if [[ $- == *i* ]]; then
  if _deckctl_tool_selected fzf && command -v fzf >/dev/null 2>&1; then
    eval "$(fzf --bash 2>/dev/null)" || true
  fi
  if _deckctl_tool_selected zoxide && command -v zoxide >/dev/null 2>&1; then
    eval "$(zoxide init bash)"
  fi
  _deckctl_prompt_engine="posh"
  if [[ -f "$HOME/.config/deckctl/terminal/prompt-engine" ]]; then
    _deckctl_prompt_engine="$(tr -d '[:space:]' < "$HOME/.config/deckctl/terminal/prompt-engine")"
  fi
  if [[ "$_deckctl_prompt_engine" == "posh" ]] && _deckctl_tool_selected oh-my-posh && command -v oh-my-posh >/dev/null 2>&1; then
    if [[ -f "$POSH_THEME" ]]; then
      eval "$(oh-my-posh init bash --strict --config "$POSH_THEME")"
    else
      eval "$(oh-my-posh init bash --strict)"
    fi
  elif _deckctl_tool_selected starship && command -v starship >/dev/null 2>&1; then
    eval "$(starship init bash)"
  fi
  unset _deckctl_prompt_engine

  ll() {
    if _deckctl_tool_selected eza && command -v eza >/dev/null 2>&1; then eza -lah --git --icons=auto --group-directories-first "$@"; else command ls -lah "$@"; fi
  }
  lt() {
    if _deckctl_tool_selected eza && command -v eza >/dev/null 2>&1; then eza --tree --level=2 --icons=auto --group-directories-first "$@"; else command find "${1:-.}" -maxdepth 2 -print; fi
  }
  cat() {
    if _deckctl_tool_selected bat && command -v bat >/dev/null 2>&1; then bat --paging=never "$@"; else command cat "$@"; fi
  }
  ff() {
    if ! command -v fastfetch >/dev/null 2>&1; then
      echo "fastfetch is not installed"; return 1
    fi
    local config="$HOME/.config/deckctl/terminal/fastfetch.json"
    local -a options=()
    if [[ -f "$config" ]]; then
      options+=(--config "$config")
    else
      options+=(--logo SteamDeck)
    fi
    command fastfetch "${options[@]}" "$@"
  }
  mkcd() { mkdir -p -- "$1" && cd -- "$1"; }

  tm() {
    if ! command -v tmux >/dev/null 2>&1; then echo "tmux is not installed; run: deckctl terminal tmux apply"; return 1; fi
    if [[ -n "${TMUX:-}" ]]; then echo "Already inside tmux: $(tmux display-message -p '#S:#I.#P' 2>/dev/null)"; return 0; fi
    tmux new-session -A -s main
  }
  tml() { command tmux list-sessions "$@"; }
  tma() {
    local session="${1:-main}"
    if [[ -n "${TMUX:-}" ]]; then command tmux switch-client -t "$session"; else command tmux attach-session -t "$session"; fi
  }
  tmk() {
    local session="${1:-main}" answer
    read -r -p "Kill tmux session '$session'? [y/N] " answer
    [[ "$answer" =~ ^[Yy]$ ]] && command tmux kill-session -t "$session"
  }
  tmhelp() {
    cat <<'TMUX_HELP'
Bubble Gum Rave tmux
  tm                 create/attach the main persistent session
  tml                list sessions
  tma [name]         attach/switch to a session (default: main)
  tmk [name]         kill a session after confirmation

Inside tmux (prefix = Ctrl+A):
  Ctrl+A |           split left/right
  Ctrl+A -           split top/bottom
  Alt+Arrow          move between panes
  Ctrl+A H/J/K/L     resize left/down/up/right
  Ctrl+A z           zoom/unzoom current pane
  Ctrl+A c           new window in current directory
  Ctrl+A n / p       next / previous window
  Ctrl+A d           detach (session keeps running)
  Ctrl+A r           reload config
  mouse drag border  resize pane
TMUX_HELP
  }

  alias c='clear'
  alias ..='cd ..'
  alias ...='cd ../..'
  alias gs='git status -sb'
  alias gd='git diff'
  alias gl='git log --oneline --decorate --graph -15'
fi
