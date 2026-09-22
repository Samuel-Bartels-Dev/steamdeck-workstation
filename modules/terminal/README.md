# Bubble Gum Rave Terminal

Use `deckctl setup customize` to choose individual tools in this category. Selections are saved in `~/.config/deckctl/components.json` and govern installation, verification, and guided setup. Deselecting a tool preserves existing installations and personal settings. Older setups without saved component choices retain their previous defaults.

A reversible user-space Konsole/Bash quality-of-life layer for the Steam Deck. It intentionally does **not** change the system shell and does not install packages with pacman.

## Shared appearance

In **Theme & appearance**, choose Bubble Gum Rave, Midnight Ocean or Graphite,
then enable the tools that should follow it. Each tool still has its independent
install choice. Appearance switches are saved in `~/.config/deckctl/appearance.json`;
off preserves existing appearance files and does not remove software. The shared
palette also reaches supported CSS Loader themes when its switch is enabled.

`deckctl terminal apply --config-only` applies selected, enabled appearance targets
without downloading tools. Reopen terminals to reload their colors and prompts.
Managed theme filenames remain stable across palettes. Personal Ghostty config
is not overwritten; use `theme = deckctl-bubble-gum-rave` to follow the palette.
Oh My Posh works in both Ghostty and Konsole when Oh My Posh and Shell helpers
are selected; the terminal emulator alone does not enable a prompt engine.

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

New or empty Ghostty configurations receive a Bubble Gum Rave coding theme:
an opaque dark background, readable ANSI colors, pink block cursor, purple
selection, 12-point text and modest padding for the Deck screen. Ghostty uses
its built-in font, so this does not require selecting the optional font download.
Existing Ghostty settings are preserved; add `theme = deckctl-bubble-gum-rave`
to your Ghostty config to use the installed theme. Reopen Ghostty after applying.
The theme uses [Ghostty's native theme format](https://ghostty.org/docs/features/theme).
Editor-specific syntax themes remain controlled by the editor.


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
The setup window lists each tool in Coding & work, alongside the separate editor Flatpaks.

See [the on-demand AI workspace](../ai-workspace/README.md) for local Ollama and
ChatGPT subscription configuration. OpenCode provider login remains interactive.

## Steam Deck Fastfetch artwork

Selecting **fastfetch** uses Fastfetch’s built-in Steam Deck artwork in hot pink and cyan.
With **Shell helpers** enabled, `ff` displays it beside your system information.
Run `deckctl terminal apply --config-only` to refresh an existing selection,
then open a new shell. The logo is included in Fastfetch; no extra image
download is needed. Personal Fastfetch configuration is preserved. Plain `fastfetch` keeps your own defaults, and `ff --logo small`
overrides the artwork for a single invocation. Nothing runs automatically at login.

The **Bubble Gum Rave** Fastfetch theme pairs pink keys, cyan/purple section
headings and pale text with the two-tone Steam Deck emblem. It shows SteamOS, model,
kernel, uptime, CPU/GPU, RAM/swap, battery, available home/external storage,
display and desktop/shell information. Hardware fields appear when detected.
The optional Konsole appearance choice supplies the matching dark background;
the Fastfetch theme works in other terminals too.

The managed theme is `~/.config/deckctl/terminal/fastfetch.json`.
After updating, select fastfetch and Shell helpers, run
`deckctl terminal apply --config-only`, then open a new shell and run `ff`.
It is a snapshot on demand, with no background monitor. Compact hardware fields
and a one-column logo gap keep it readable on the Deck; long values are
shortened and line wrapping is disabled while rendering to protect the artwork.
Run plain `fastfetch` when you need the full hardware strings.

## Repeat installs and updates

Normal apply checks release metadata for healthy selected tools. Matching or
newer installed numbered versions skip payload downloads; newer upstream
versions update. Missing tools install, and untracked/modified binaries stay
protected. Unknown version formats and offline checks retain installed tools
with a message instead of guessing. `--refresh` also checks versions and no
longer forces a redundant download. `--config-only` avoids update checks.

Shell-installer tools are installed in staging and pass a version check before
replacing the managed executable. Temporary files are removed. AppImages and
older Ollama runtimes are executable/recovery payloads, not disposable download
archives; they are retained.

The per-item setup window reports download bytes, archive extraction, configuration
and verification phases where the provider exposes them. Elapsed time continues
during opaque provider operations; a spinner never claims a percentage. **View log**
shows phase notes and stderr/Python errors while Konsole keeps interactive prompts.
