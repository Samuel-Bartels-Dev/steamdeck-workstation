# Regression Matrix

These are user-visible contracts that must remain true across releases. `deckctl repo validate` includes automated guardrails for the highest-risk items.

## Provisioning core
- `install.sh` runs as the normal `deck` user; narrow operations may request sudo.
- `deckctl` is persisted at `~/.local/bin/deckctl`; extracted release folders are disposable after provisioning.
- Guided setup is resumable and completed steps are revalidated; stale state is re-offered.
- Desktop Mode owns shell/provisioning work. Game Mode instructions never require `deckctl` commands.

## Decky
- A bare `~/homebrew` directory is **not** proof that Decky Loader is installed.
- Decky Loader is verified from the real loader/service state.
- Desired plugin selection lives only in `~/.config/deckctl/decky-selection.json`.
- Desktop checklist `.txt` files are not created and are never treated as state.
- Selected plugins are reconciled from Decky's trusted Store artifacts, validated, installed atomically, and then verified from actual plugin folders.
- Plugin folders without Decky Loader are reported `ORPHANED`, never `INSTALLED`.
- Bubble Gum Rave files are installed in Desktop Mode; CSS Loader Theme Store enable/profile actions happen in Game Mode.

## Controller
- Controller templates install inline during guided setup.
- Fresh Desktop setup does not require an immediate Steam restart; switching to Game Mode naturally reloads Steam. Restart is only a fallback if a template remains missing.

## Media / Keeper
- Netflix, Hulu, Crunchyroll, and Prime Video use Chrome `--kiosk` with the persistent normal Chrome profile.
- KeeperFill is user-installed/signed-in in that profile; deckctl stores no Keeper credentials.

## Terminal
- Bash remains the default shell.
- Starship, zoxide, fzf, eza, bat, fastfetch, Nerd Font, Konsole Bubble Gum Rave profile, and tmux are user-space managed/reversible.
- tmux is opt-in (`tm`), not auto-launched for every Konsole.
- tmux uses Ctrl+A prefix, split/navigation helpers, same-directory panes, mouse support, and persistent sessions.

## Recovery / lifecycle
- CSS Loader profiles can be captured/restored.
- UI safe mode can fall back from heavy styling.
- `post-update` rechecks Decky/CSS/controller/terminal state.
- deckctl supports versioned update and rollback.
- profile export/import excludes secrets.
- support bundle excludes browser/Keeper data, credentials/tokens, ROMs, BIOS/firmware, private keys, shell history, and sensitive remote-host details.

## Storage / emulation
- Emulation migration preflights and hands off to EmuDeck's supported migration workflow.
- Finalization does not immediately delete the old Emulation tree; it preserves a rollback copy first.

## Remote / host kit
- Tailscale/Moonlight/Sunshine are the core remote stack.
- Windows Sunshine host tooling lives under `host/windows/` and is never executed by Deck `install.sh` or included in the Deck module dependency graph.

## Validation before release
1. `./bin/deckctl repo validate`
2. Bash syntax check across all `*.sh`
3. JSON parse across all `*.json`
4. Build release archive
5. Extract archive to a clean directory
6. Rerun `./bin/deckctl repo validate` from extracted bytes
7. Rerun Bash syntax checks from extracted bytes
8. Build USB bundle from that validated tarball

## Battle.net targeted install
- Choosing Battle.net in guided setup invokes NonSteamLaunchers with the exact `"Battle.net"` launcher argument.
- Guided setup must not open the generic NSL launcher checklist for this path.
- A staged `NonSteamLaunchers.desktop` file is never installation proof.
- Completion requires the real Battle.net executable under a supported Steam compatdata prefix.
- `deckctl launcher install battlenet` must remain available as the direct repair/manual command.
