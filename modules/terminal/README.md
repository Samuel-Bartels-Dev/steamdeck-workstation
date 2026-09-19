# Bubble Gum Rave Terminal

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
