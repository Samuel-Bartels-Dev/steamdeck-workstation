# Bubble Gum Rave Terminal

Use `deckctl setup customize` to choose individual tools in this category. Selections are saved in `~/.config/deckctl/components.json` and govern installation, verification, and guided setup. Deselecting a tool preserves existing installations and personal settings. Older setups without saved component choices retain their previous defaults.

A reversible user-space Konsole/Bash quality-of-life layer for the Steam Deck. It intentionally does **not** change the system shell and does not install packages with pacman.

## Managed components

- JetBrainsMono Nerd Font Mono in `~/.local/share/fonts/deckctl-jetbrainsmono`
- Oh My Posh prompt (default) with a repo-owned Bubble Gum Rave theme for PWD/Git/status/time context
- Starship remains installed as a fallback prompt engine and can be selected without reinstalling tools
- zoxide (`z`, `zi`) for ranked directory jumping
- fzf with Bash key bindings/completion (`Ctrl-R`, `Ctrl-T`, `Alt-C`)
- eza (`ll`, `lt`)
- bat-backed interactive `cat`
- fastfetch (`ff`)
- safe helper aliases/functions (`c`, `..`, `...`, `gs`, `gd`, `gl`, `mkcd`)
- a separate `Bubble Gum Rave` Konsole profile/color scheme

All downloaded binaries go to `~/.local/bin`. The module keeps Bash as the default shell and leaves the stock Konsole profile installed as a recovery path.

## Commands

```bash
deckctl terminal status
deckctl terminal apply
deckctl terminal prompt status
deckctl terminal prompt use posh
deckctl terminal prompt use starship
deckctl terminal font-check
deckctl terminal reset
deckctl terminal reset --keep-tools
```

Oh My Posh is the default. Only one prompt engine is initialized at a time; selecting Starship is a fallback, not a second prompt layered on top.

`reset` removes only managed binaries whose hashes still match the installation receipts; modified/untracked files are preserved rather than deleted.

## tmux persistent workspace

The module also installs a user-local static tmux build from the official `tmux/tmux-builds` project and a marker-managed `~/.tmux.conf` include. It does not start tmux automatically when Konsole opens.

```bash
tm                    # create/attach persistent main session
tml                   # list sessions
tma [name]            # attach/switch
tmk [name]            # kill after confirmation
tmhelp                # key cheat sheet

deckctl terminal tmux status
deckctl terminal tmux apply
```

Primary pane controls:

```text
Ctrl+A |           split left/right
Ctrl+A -           split top/bottom
Alt+Arrow          move between panes
Ctrl+A H/J/K/L     resize panes
Ctrl+A z           zoom/unzoom
Ctrl+A c           new window in current directory
Ctrl+A d           detach; session keeps running
Ctrl+A r           reload tmux config
```

Mouse support is enabled, panes inherit the current working directory, and the status/pane borders use the Bubble Gum Rave palette. The managed config requests RGB color and OSC-52 clipboard integration where the outer terminal supports it.

## Coding tools

`deckctl terminal apply` installs only the chosen tools. Ghostty, Neovim (`nvim`),
OpenCode (`opencode`), tmux, each prompt/helper tool, fonts, shell integration, and
Konsole appearance are independent choices. Selecting Ghostty alone does not
change Bash, tmux, or the Konsole default profile. No coding app or tmux server
is started at login. Ghostty gets its own Desktop Mode menu entry, while Konsole
remains available. Existing personal Ghostty/Neovim settings are not replaced.

Ghostty uses the community AppImage linked by [Ghostty's Linux install docs](https://ghostty.org/docs/install/binary).
Neovim uses its [official AppImage](https://neovim.io/doc/install/), retaining the
full editor runtime. Both wrappers request AppImage extract-and-run mode so they
do not require a working FUSE mount. OpenCode uses its official Linux x64 baseline
archive from `anomalyco/opencode`. New downloads require the release asset SHA-256
and pass a version check before replacing a managed executable. Untracked user
binaries are preserved. Terminal status executes version checks for these tools.

AppImages live in `~/.local/share/deckctl/terminal-appimages`. Reset removes only
unchanged managed wrappers/binaries and the unchanged managed Ghostty menu entry;
AppImage payloads and personal editor configuration are retained for recovery.
The desktop Flatpak chooser does not control these terminal-module tools.

See [the on-demand AI workspace](../ai-workspace/README.md) for local Ollama and
ChatGPT subscription configuration. OpenCode provider login remains interactive.

## Sharingan Fastfetch artwork

Selecting **fastfetch** installs a compact red Sharingan-inspired ASCII eye.
With **Shell helpers** enabled, `ff` displays it beside your system information.
Run `deckctl terminal apply --config-only` to refresh an existing selection,
then open a new shell. The managed art lives at
`~/.config/deckctl/terminal/sharingan.txt`; personal Fastfetch configuration is
preserved. Plain `fastfetch` keeps your own defaults, and `ff --logo small`
overrides the eye for a single invocation. Nothing runs automatically at login.
