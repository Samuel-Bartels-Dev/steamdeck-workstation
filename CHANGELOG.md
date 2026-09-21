# v0.2.33

- Add a staged Steam Deck setup builder with optional feature groups, desktop app selection, a KDE chooser, terminal fallback and review screen.
- Allow base-only or repository-default plans; skipped setup stages no longer block readiness or trigger unselected optional provisioning.

See docs/RELEASE-0.2.33.md.

# v0.2.32

- Add a staged setup builder for optional modules and desktop apps, with a native KDE chooser, terminal fallback, review screen and base-only/full-default presets.
- Make skipped features explicit in guided setup status and allow users to tailor a Deck later without uninstalling existing apps.
- Install Ghostty, Neovim and OpenCode in the terminal module; keep tmux available.
- Add an on-demand rootless Ollama/OpenCode workspace and small local coding model.
- Add managed Moonlight and Battle.net Desktop icons.

See docs/RELEASE-0.2.32.md.

# v0.2.31

- Add Discord and Slack to selectable desktop installs, verification and settings-preserving uninstall.
- Preserve existing saved app selections when the catalog grows.

See docs/RELEASE-0.2.31.md.

# v0.2.30

- Add persistent desktop app selection to the installer and CLI.
- Add targeted user-app removal with preview, preserved settings and reinstall prevention.

See docs/RELEASE-0.2.30.md.

# v0.2.29

- Add Zen Browser, Zed, VLC, Plex Desktop and Spotify to user Flatpak installs.
- Detect missing desktop apps, propagate install failures and safely retry partial installs.

See docs/RELEASE-0.2.29.md.

# v0.2.28

Docker storage repair, familiar commands and d/dc aliases, guided overlay recovery,
separate API and tested-container readiness, and a short Docker guide.
See docs/RELEASE-0.2.28.md.

# v0.2.27

Publish the optional Docker/Compose support already merged into main, so the stable
bootstrap can install it. Includes PR lint gates, hardware/compatibility reporting,
and scoped MIT licensing. See docs/RELEASE-0.2.27.md.

# v0.2.26

Provisioning resume/report, upgrade preview, shortcut repairs, verified restore and
SD migration, and public GitHub distribution. See docs/RELEASE-0.2.26.md.

# v0.2.25

- Add the requested Decky plugins and correct Controller Tools Store identity.
- Upgrade saved selections once while preserving later opt-outs and settings.
- Preserve v0.2.24 provisioning, cleanup, Android, CSS and recovery behavior.

# v0.2.24

- Remove installer-wide chmod that changed sourced terminal configuration from 0644 to 0755 before running preservation tests.
- Preserve package modes and keep validation strict; verify installer preflight in an isolated executable shell harness.
- Retain v0.2.23 existing-install fixes, cleanup, and all CSS/Waydroid behavior.

# v0.2.23

- Clean verified, unchanged installer shortcuts; skip EmuDeck bootstrap when its installed manager and vendor completion markers are present.
- Remove the updater-owned unchanged tarball after successful promotion; retain explicit user archives and rollback releases.

- Fix pre-install regression tests reading the host Decky service while simulating a system without Decky.
- Isolate regression subprocess HOME, deckctl configuration/state, and XDG paths.
- Test enabled, disabled, failed, and executable-based Loader detection independently.
- Verify existing-install control-plane upgrade, repeated install, data preservation, and prior-release retention.
- Preserve all v0.2.22 provisioning, CSS selection, Waydroid first-launch, and recovery behavior.

# v0.2.22

- Complete Waydroid first-run setup through the vendor bundled launcher during provisioning; preserve host repair, images, and user data.
- Route the staged Android setup shortcut through the same protected deckctl workflow.
- Install Art Hero, Clean Gameview, Clean Game Launch, and Focus Highlight Color by default; remove Colored Toggles from the managed selection.
- Attempt every selected CSS component, report individual failures, and require complete saved-state verification before success.
- Retain detailed command help, recovery features, Desktop icons, and SteamGridDB artwork ownership.

# v0.2.21

- Fix installer preflight failure on Python 3.13: canonicalize generated manual synopsis wrapping without disabling documentation drift checks.
- Run CI on Python 3.12 and 3.13 and add manual consistency regressions.
- Clearly distinguish pre-install validation from provisioning in installer output.
- Preserve v0.2.20 functionality, detailed help, all modules, and unchanged Waydroid.

# v0.2.20

- Review the full repository while preserving all 16 modules and the unchanged Waydroid subsystem.
- Document every command/group with detailed runtime help, `deckctl help PATH`, `--version`, generated Markdown, and an installed man page.
- Make help/status inspection read-only and propagate installer/verifier/recovery failures accurately.
- Harden profile export/import, archive extraction, backup restore, rollback selection, and persistent release installation.
- Preserve working terminal binaries during failed updates; constrain receipt-driven cleanup; retain Tailscale setup files during failed refreshes.
- Correct remote SSH quoting and host-kit path validation, Desktop Exec escaping, and repeated emulation finalization behavior.
- Add 30 behavioral tests, exhaustive command help checks, manual drift checks, local documentation-link validation, and explicit v0.2.19 preservation guards.

# v0.2.19

- Replace the incorrect standalone Bubble Gum Rave CSS theme with palette settings
  on real CSS Loader Theme Store components, using the installed plugin's native
  download/configuration/profile methods and live plus persisted-state validation.
- Preserve the existing Decky selection/Store installer; reject incomplete plugin
  folders and false-positive service detections. SteamGridDB remains the Gaming
  Mode artwork owner (including the request called SteamDeckDB).
- Bundle distinct Desktop SVG icons, reconcile project media/workspace shortcuts,
  and leave Steam artwork untouched.
- Preserve all 16 baseline modules and Waydroid byte-for-byte. Retain terminal,
  controller, storage, remote, recovery, export/import and sanitized support tooling.
- Build the exact repository tar, USB ZIP with README-first/installer/nested tar,
  and SHA-256 manifest. Add behavioral regression and extracted-package checks.

# 0.2.18

- Fix Android/Waydroid completion hanging after a successful install when `steamos-add-to-steam` launches or owns a long-running Steam process.
- Waydroid shortcut submissions are now detached from the installer process tree while upstream keeps its bounded shortcut polling.
- Android readiness is explicitly image + user-state based; Steam shortcut visibility is reported separately as `FOUND`, `PENDING_STEAM_REFRESH`, or `UNKNOWN`.
- `deckctl android status` now explains that a pending shortcut does not require reinstalling Android.
- Add regression coverage for non-blocking Waydroid Steam shortcut handoff.

# 0.2.17

- Fixed Fastfetch installation on current upstream Linux archives that contain multiple files named `fastfetch`; `deckctl` now selects the canonical `usr/bin/fastfetch` payload deterministically.
- Added post-install execution verification (`fastfetch --version`) before Fastfetch is recorded as healthy.
- Added a regression smoke test with duplicate Fastfetch basenames so the archive-layout failure cannot silently return.
- `ff` remains a shell helper for the real `fastfetch` binary; it is not itself the downloaded executable.

# 0.2.16

- Added Oh My Posh as the default Bubble Gum Rave prompt engine using the official user-local Linux installer and a repo-owned local theme.
- Starship remains installed as a fallback; the shell initializes exactly one prompt engine at a time.
- Added `deckctl terminal prompt status` and `deckctl terminal prompt use posh|starship`, plus `dposh` / `dstarship`.
- Added regression guardrails for the Oh My Posh binary, local theme, Bash `--strict` init path, prompt-engine selector, and aliases.

# Changelog

## 0.2.15
- Adds first-class Android commands: `status`, `install`, `retry`, `repair`, and protected `reinstall`.
- Android guided setup now requires both the Waydroid persistent image and Android user state before it can be marked ready.
- Fresh Android guidance explicitly recommends Android 13 with Google Play.
- Reworks `deckctl -h` into grouped workflows with common examples and richer Android/workspace subcommand help.
- Adds managed Desktop workspace app-window shortcuts for Notion, ChatGPT, and Claude using the persistent Chrome profile.
- Adds `deckctl workspace notion-mcp` guidance for connecting authorized AI clients to Notion without storing tokens in the repo.
- Adds regression guardrails for Android readiness/retry, workspace apps, and rich CLI help.


- Fixed media guided setup looping/hanging, most visible on Prime Video.
- Media reconciliation now runs inline instead of opening a keep-alive Konsole that drops into an interactive shell afterward.
- Desktop provisioning succeeds when all four kiosk launchers/runners exist; Steam shortcut visibility is audited separately after Steam refresh.
- Added per-service submission receipts so a pending Steam shortcut is not submitted repeatedly on every reconcile.
- `deckctl media status` now reports `PENDING STEAM REFRESH` instead of treating a submitted-but-not-yet-visible shortcut as missing.
- Added regression guardrails preventing media setup from using the generic keep-open terminal path or invoking unrelated BIOS/update workflows.

# 0.2.13

- Changed guided Battle.net provisioning to use NonSteamLaunchers' supported launcher-name CLI argument (`"Battle.net"`) instead of opening the full launcher checklist.
- Added `deckctl launcher install battlenet` for the same targeted install path.
- Battle.net completion now verifies the real Battle.net executable under either NSL's shared `NonSteamLaunchers` prefix or the separate `Battle.netLauncher` prefix; a staged NSL desktop helper never counts as installed.
- The generic `NonSteamLaunchers.desktop` remains staged only as an advanced/manual fallback for installing other launchers.
- Added regression guardrails so the guided Battle.net step cannot regress back to the full NSL picker or staged-file detection.

# 0.2.12

- Fixed misleading Controller Templates first-run UX. A successful copy no longer tells users to restart Steam/Game Mode during Desktop provisioning.
- Controller template installation now runs inline as a non-interactive guided step instead of opening a second Konsole window.
- Guided setup immediately verifies `Deck Desktop Mouse.vdf` after installation and marks the step complete on success.
- Fresh-install guidance now says to continue Desktop setup normally; switching to Game Mode later provides the normal Steam UI reload, with a manual Steam restart only as a fallback if the template is still absent.

# 0.2.10

- Added tmux as a first-class part of the managed terminal toolbox, installed user-locally from the official `tmux/tmux-builds` static Linux release rather than mutating SteamOS with pacman.
- Added a Bubble Gum Rave tmux configuration with mouse support, RGB styling, same-directory splits/new windows, 100k history, pane borders/status bar, and external clipboard integration where Konsole supports it.
- Changed the tmux prefix to `Ctrl+A`; `Ctrl+A |` splits left/right, `Ctrl+A -` splits top/bottom, `Alt+Arrow` navigates panes, `Ctrl+A H/J/K/L` resizes, `Ctrl+A z` zooms, and `Ctrl+A d` detaches.
- Added shell helpers `tm`, `tml`, `tma`, `tmk`, and `tmhelp` plus `deckctl terminal tmux status|apply` and alias `dtermux`. tmux remains opt-in per terminal session; Konsole still opens as a normal Bash shell.
- tmux configuration is injected through marker-managed `~/.tmux.conf` lines that source the repo-owned config, preserving unrelated user configuration and making reset reversible.

# 0.2.9

- Added a first-class `terminal` module for reversible Steam Deck Konsole/Bash polish without changing the default shell or mutating SteamOS with pacman.
- Added JetBrainsMono Nerd Font Mono, Starship, zoxide, fzf, eza, bat, and fastfetch as user-local tooling under `~/.local`.
- Added a repo-owned Bubble Gum Rave Starship prompt with compact PWD/repo context, Git status, language runtimes, command duration, battery, time, and success/error prompt states.
- Added a separate Bubble Gum Rave Konsole profile/color scheme with the Nerd Font, dark OLED-friendly palette, current-directory tab inheritance, and expanded scrollback. The stock Konsole profile remains available.
- Added Bash-only managed shell integration: fzf key bindings/completion, zoxide `z`/`zi`, and safe convenience helpers `ll`, `lt`, `cat`→bat, `ff`, `mkcd`, `c`, `..`, `...`, `gs`, `gd`, and `gl`.
- Added `deckctl terminal status|apply|reset|font-check` plus `dterminal`, `dtermapply`, and `dtermreset`. `reset` removes only still-matching managed payloads and preserves modified/untracked files.
- `post-update` now reasserts terminal presentation/config without redownloading tools, and sanitized support bundles include terminal readiness metadata but never shell history.

# 0.2.8

- Added CSS Loader profile capture/restore: `deckctl decky css profiles|capture|restore` plus `dcsscapture` / `dcssrestore`.
- Added UI safe mode and restore. Normal safe mode quarantines the heavy optional CSS stack; `--minimal` quarantines all managed CSS layers/live profiles for emergency recovery without deleting them.
- Added `deckctl post-update` / `dpostupdate` to reconcile Decky, selected plugins, Bubble Gum Rave, captured CSS profiles, controller templates, and health after SteamOS updates.
- Added versioned `deckctl update check|apply|rollback`. Archive updates validate the candidate repo before switching the persistent `current` control-plane symlink; GitHub auto-update remains disabled until a release repo is explicitly configured.
- Added portable `deckctl profile export|import`, including desired-state/configuration and captured CSS/controller metadata while excluding browser/Keeper credential stores, cookies, ROMs, BIOS/firmware, and private keys.
- Replaced the old support-bundle path with a sanitized manifest bundle that explicitly redacts sensitive keys and excludes browser profiles, Keeper data, save payloads, private content, and remote-host target/MAC data.
- Added a guided KeeperFill Chrome-extension step plus `deckctl media keeper setup|status` / `dkeeper`. Installation opens Keeper Security's official Chrome Web Store page and requires normal Chrome user consent/sign-in; `deckctl` never stores Keeper credentials.
- Media Game Mode shortcuts use Chrome `--kiosk` with the normal persistent Chrome profile. This preserves the clean single-site Game Mode UI while allowing an installed/unlocked Keeper extension to autofill matching site records.

# 0.2.7

- Expanded the managed Bubble Gum Rave CSS stack with the requested Theme Store polish: Centered Game Text, DellyVolume, Better Game Icons, Better Game Badges, Top Bar Transparency, Better Blur, Better Achievements, Game Cover Reflections, Percentages, and No Game Count.
- Kept Art Hero, Clean Gameview, and Clean Game Launch as the heavier optional layout group, alongside Hero Zoom Eradication, No Home Edge Fade, Mini Carousel, Gradient Top Bar, Game Cover Shine Animation, Tilted Home, DellyFooter, Static Background, and Faster Transition Animations.
- Added per-theme starting-setting guidance to `css-stack.json`; `deckctl decky css status` and `deckctl decky css guide` now print those starting points.
- Updated the deterministic CSS load order with Bubble Gum Rave remaining last as the palette/focus override layer.
- Added a two-profile operating model: save `Bubble Gum Rave - Base` before enabling heavier home/game-detail layout themes, then optionally save `Bubble Gum Rave - Full`.
- Clarified that `Top Bar Transparency` is the baseline treatment while `Gradient Top Bar` is an alternative, not something to stack blindly.

# 0.2.6

- Added a managed **Bubble Gum Rave / Chromahon CSS stack** manifest.
- Bubble Gum Rave is now split into `steam-menu.css`, `qam.css`, `context-menus.css`, `input-controls.css`, and shared palette rules for easier post-Steam-update troubleshooting.
- Tracks Chromahon Steam Menu, Input Controls, Context Menus, and QAM as the required structural layer.
- Tracks Colored Toggles, Round, and Full Screen Menus as the recommended compatible polish layer.
- Tracks Art Hero, Clean Gameview, Better Game Icons, Gradient Top Bar, Game Cover Shine Animation, Tilted Home, Delly Footer, and Delly Volume as optional home/library polish.
- Added `deckctl decky css status` / `dcss` and `deckctl decky css guide` / `dcssguide`.
- Theme installation now writes `~/Desktop/Bubble Gum Rave CSS Stack.txt` with the Game Mode setup order.
- Bubble Gum Rave remains independently loadable rather than hard-depending on community themes; enable it last so its palette overrides structural themes safely.
- README now explains creating a CSS Loader Profile named `Bubble Gum Rave` after the stack is configured.

# 0.2.5

- Fixed the post-install flow incorrectly implying that `deckctl` commands should be run from Game Mode. `deckctl` is a Desktop Mode/Konsole command.
- Guided setup now installs Bubble Gum Rave theme files in Desktop Mode immediately after selected Decky plugins are reconciled.
- Updated Decky selector, checklist, audit, module docs, and final setup messaging to reflect automated plugin installation; the Game Mode Plugin Store is fallback-only for unresolved items.
- Final Game Mode instructions now contain only Game Mode-native actions: verify Decky plugins, refresh/enable Bubble Gum Rave in CSS Loader, and complete UI sign-ins/testing.

# Changelog

## 0.2.4

- Restored the README to a copy/paste-first operator format.
- Added explicit fresh-install, upgrade/reconcile, resume, Decky retry, controller-template, migration, remote, backup/restore, and health command blocks.
- Added a clear warning not to run the full installer as root; sudo is requested only for narrow privileged operations.
- Restored a detailed USB `README-FIRST.txt` workflow in the release bundle.

# 0.2.3

- Fixed automated Decky plugin installation on systems where `~/homebrew/plugins` is not writable.
- `deckctl decky install-selected` now detects that condition and prompts for sudo only for a narrow ownership/permission repair of the Decky plugin directory.
- The rest of `deckctl` continues to run unprivileged; Decky service files under `~/homebrew/services` are never recursively re-owned.

# Changelog

## 0.2.2

- Added `deckctl decky install-selected` and alias `dplugininstall` so the checkbox-selected Decky desired state can be installed automatically instead of only audited.
- Automatic plugin installation resolves artifacts from Decky's official Plugin Store catalog/CDN rather than arbitrary GitHub URLs.
- Added ZIP safety/identity validation, path-traversal and symlink rejection, unpacked-size limits, required Decky package-file validation, atomic staging/backups, install receipts, and a single Decky Loader restart after the batch.
- Added `deckctl decky receipts` for provenance/debugging.
- If a selected Store artifact cannot be resolved or safely validated, the plugin remains MISSING and the normal Decky Plugin Store is the fallback; no forced install and no automatic removals.
- Guided setup now has an explicit `Install selected Decky plugins` reconciliation step after the checkbox selector.

## 0.2.1

- Fixed guided Controller Templates failing with `deckctl: command not found` in a fresh Konsole/login shell.
- Guided terminal commands now explicitly prepend `~/.local/bin` to PATH instead of assuming `.bashrc` has been sourced.
- Controller Templates now invokes the absolute persistent `~/.local/bin/deckctl` path, with the repo-local CLI as a fallback.

## 0.1.9

- Added a persistent Decky plugin desired-state selector with KDE checkbox dialogs grouped into Core, Recommended, and Optional.
- Core + Recommended default selected; Optional defaults unselected, but every item can be changed.
- Each checkbox includes the plugin what/why blurb from the manifest.
- Selection persists in `~/.config/deckctl/decky-selection.json` and creates `~/Desktop/Decky Selected Plugins.txt`.
- `deckctl decky plugins` now audits the user-selected desired set and reports installed, missing, extra, and not-selected plugins.
- Added `deckctl decky selected` and alias `dpluginselect`.
- Moved aliases to `config/aliases.json` so the shell bootstrap and `deckctl aliases` share one source of truth.
- Guided first-run setup now includes the plugin selection screen after Decky Loader.
- Plugin payload installation remains through Decky's supported Plugin Store; no private bulk-install API dependency was introduced.

## 0.1.8

- Finalized Decky plugin policy and emitted it in the release instead of leaving it only in conversation.
- Default/recommended Decky set now includes HLTB for Deck, AutoFlatpaks, Bluetooth, Emuchievements, Non-Steam Badges, Animation Changer, Audio Loader, Deck Settings and EmuDecky.
- MoonDeck moved to optional: standard Tailscale + Moonlight + Sunshine remains the core remote-gaming path; MoonDeck Buddy is only needed when MoonDeck is enabled.
- Optional list now includes ControllerTools, Deck Shelves, Tailscale Control, Storage Cleaner, vibrantDeck, Fantastic, AutoSuspend, Battery Tracker, Pause Games, Volume Mixer and BetterKeyboard.
- PowerTools policy explicitly leaves global SteamOS CPU/SMT/GPU/power settings unchanged; tuning is per-game/per-emulator only.
- Clarified safe defaults for AutoFlatpaks, Storage Cleaner, vibrantDeck, Fantastic and Pause Games.

## 0.1.7
- Promote HLTB for Deck, AutoFlatpaks, Bluetooth, Emuchievements, Non-Steam Badges, Animation Changer, Audio Loader, MoonDeck, and Deck Settings to the default recommended Decky set.
- Keep ControllerTools, Deck Shelves, Tailscale Control, Storage Cleaner, AutoSuspend, vibrantDeck, and Fantastic visible as optional choices.
- Add `modules/decky/plugin-policies.json` with explicit install/configuration policy for every curated plugin.
- Define PowerTools as per-game/per-emulator only: no global SMT/GPU/CPU/power overrides during provisioning.
- Define AutoFlatpaks as notify/check by default with unattended upgrades disabled.
- Define MoonDeck as install-by-default but configuration-required until MoonDeck Buddy is configured on a Sunshine host.
- Add Deck Settings as an advisory source for game-specific compatibility/performance guidance without automatic mutation.

## 0.1.6
- Install the control plane persistently under `~/.local/share/steamdeck-workstation/releases/<version>` and expose `deckctl` through `~/.local/bin`.
- Add idempotent bash/zsh aliases for common `deckctl` workflows and `deckctl aliases`.
- Add a curated Decky plugin manifest and `deckctl decky plugins` status audit.
- Add the version-controlled **Bubble Gum Rave** CSS Loader theme for QAM, context menus, focus states, input controls, sliders, toggles, and menu surfaces.
- Add `deckctl decky theme install|status`.
- Tighten Decky detection so a bare `~/homebrew` folder does not count as an installed loader.
- Continue using Decky's supported Plugin Store for plugin installation instead of private plugin-folder hacks.

## 0.1.5

- Fixed media provisioning so Netflix, Hulu, Crunchyroll, and Prime Video create real Steam/Game Mode shortcuts instead of only staging a launcher.
- Media shortcuts now use `~/.local/share/applications`, SteamOS `steamos-add-to-steam`, and a Steam URI fallback; reruns avoid obvious duplicates and verification checks Steam shortcut state.
- Fixed Codex provisioning: Codex is installed directly on the SteamOS user account with OpenAI's standalone Linux installer and no longer depends on Distrobox/npm.
- Added official GitHub-release fallback for Codex installation plus `codex login status` authentication verification.
- Guided setup now re-verifies a step after the visible installer closes and does not silently mark an unverifiable step complete.

## 0.1.4

- Fixed Tailscale provisioning on SteamOS: Discover/Flatpak is no longer used or suggested.
- Added a staged `Install-Tailscale.desktop` helper that fetches `tailscale-dev/deck-tailscale`, runs its persistent SteamOS installer, and performs QR authentication.
- Added a git-free archive fallback for factory-fresh Decks.
- Improved remote verification to detect `/opt/tailscale/tailscale` even when the current shell has not sourced the upstream profile fragment.

## 0.1.3

- Add optional `media` module for Netflix, Hulu, Crunchyroll, and Prime Video in Steam Game Mode.
- Add fullscreen Chrome web-app launchers with user-space SteamOS input permissions.
- Auto-add media shortcuts to Steam when `steamos-add-to-steam` is available.
- Add `deckctl media setup` and `deckctl media status`.
- Document browser/DRM limitations and Steam Input/SteamGridDB polish.

## 0.1.2 — 2026-09-16

- Added first-class Android gaming module using the SteamOS-specific Waydroid bundle.
- Added guided Android 13 + Google Play flow for Pokémon Champions.
- Added Waydroid repair/verification semantics for SteamOS updates.
- Added automatic Codex CLI installation inside `deck-dev` when Distrobox is available.
- Added guided Codex authentication step.

## 0.1.1
- Replaced the manual `~/Desktop/Deck-Setup-Staged` handoff with `deckctl setup run`.
- Added resumable guided setup state and a Desktop resume shortcut.
- Added automatic launching/fallback handling for Heroic, Battle.net/NonSteamLaunchers, Decky, EmuDeck, Tailscale guidance, Moonlight, and chiaki-ng.
- `install.sh` now transitions directly into guided setup.


## 0.1.0

Initial Steam Deck workstation provisioning platform skeleton.

- Hardware-aware OLED/LCD profiles.
- Module contract and dependency orchestration.
- Steam/Heroic/Battle.net guidance.
- Decky, EmuDeck, Moonlight, chiaki-ng, Tailscale, Distrobox/Codex flows.
- Storage roles, health checks and recommendation command.
- Game ready/doctor scaffolding.
- Remote wake/quality checks.
- Save protection, travel mode, support bundle and AI context/task helpers.

## 0.2.0

Pre-1.0 lifecycle-completion release.

- Added Controller Profile Manager with Steam Input recommendation, discovery, capture, template installation, and controller-page helpers.
- Added supported EmuDeck internal-to-`DECK-EMU` migration orchestration with verification-first rollback preservation.
- Added Steam non-Steam shortcut/artwork auditor for grid/portrait/hero/logo/icon coverage.
- Added v2 state backups and a selective restore wizard.
- Added Flatseal as the standard Flatpak permission-recovery utility.
- Added network diagnostics and unified `deckctl health`.
- Added Windows Sunshine host companion kit. It is packaged in the repo and can be exported with `deckctl remote host-kit`, but Steam Deck `install.sh` never executes it.
- Added aliases: `dhealth`, `dnetwork`, `drestore`, `dcontroller`, `dlibrary`, `dmigrate`, and `dhostkit`.
