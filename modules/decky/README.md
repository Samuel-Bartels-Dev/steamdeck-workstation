# Decky Module

Every plugin is optional, including the Core and Recommended lists below. In `deckctl setup customize`, enable Decky and open **Choose plugins** to select any subset or clear all. Explicit selections remain authoritative across future manifest updates. Choosing zero plugins keeps only the selected Decky Loader setup; unchecking Decky skips that too. Existing plugins are never removed.


Decky is an enhancement layer, never a core dependency. Steam, games, remote access and recovery should continue to work if Decky is temporarily broken.

## Policy

- Install Decky Loader with its supported stable installer.
- Preferred source of plugin artifacts is Decky's official Plugin Store. `deckctl decky install-selected` can automate selected missing plugins from the Store catalog/CDN after validating the standard Decky ZIP layout.
- If an artifact cannot be resolved or validated, fall back to Decky's built-in Plugin Store UI rather than forcing the install.
- `deckctl decky select` opens a three-section checkbox selector (Core / Recommended / Optional) and saves desired state only to `~/.config/deckctl/decky-selection.json`. No Desktop checklist file is used as proof of installation.
- `deckctl decky plugins` audits the saved desired set and shows the policy for each plugin.
- Automated direct installs are limited to artifacts currently published by Decky's official Store, installed atomically into `~/homebrew/plugins` with receipts/backups. Arbitrary third-party URLs are not accepted by this path.
- Real CSS components are downloaded by CSS Loader itself through its Theme Store mechanism.

## Curated plugin set

### Core — install by default

- CSS Loader — manages real Theme Store components and their Bubble Gum Rave color settings.
- SteamGridDB — artwork for non-Steam/Heroic/media/emulation/remote shortcuts.
- ProtonDB Badges — compatibility information.
- PowerTools — installed for per-game/emulator tuning; **no global tuning is applied**.

### Recommended — install by default

- HLTB for Deck
- AutoFlatpaks
- Bluetooth
- Emuchievements
- Non-Steam Badges
- Animation Changer
- Audio Loader
- Deck Settings
- EmuDecky
- Controller Tools
- Game Theme Music
- MagicPods
- TabMaster

### Optional — visible but not required

- MoonDeck — only if you want tighter per-game Moonlight integration. MoonDeck Buddy lives on the streaming PC. Plain Moonlight + Sunshine does not need it.
- Deck Shelves
- Tailscale Control
- Storage Cleaner
- vibrantDeck
- Fantastic
- AutoSuspend
- Battery Tracker
- Pause Games
- Volume Mixer
- BetterKeyboard

## PowerTools policy

Install it, but leave the global Deck state alone. SteamOS remains authoritative for CPU/GPU/power defaults. PowerTools is useful because it stores profiles per game.

Use it only after a title/emulator actually benefits from a measured change. EmuDeck may recommend changes such as SMT off or a manual GPU frequency for some emulators; save those as per-game/per-emulator profiles rather than turning them into a global Deck tweak.

## Other plugin defaults

- **AutoFlatpaks:** update checks/toasts are useful; unattended broad auto-updates remain off, especially around travel.
- **Bluetooth:** install-only convenience surface; SteamOS remains the Bluetooth owner.
- **Emuchievements:** connect RetroAchievements only if you use it; credentials never enter this repo.
- **Animation Changer / Audio Loader:** install now; keep stock content until our curated Bubble Gum Rave packs exist.
- **Deck Settings:** advisory only. Do not automatically apply community performance settings.
- **EmuDecky:** recommended because this Deck uses EmuDeck; it exposes hotkeys, quick settings and emulator updates in Game Mode.
- **MoonDeck:** optional. Use only if the extra one-click host-game integration is worth installing MoonDeck Buddy on the PC.
- **Storage Cleaner:** manual review only; never auto-delete compatdata or shader cache.
- **vibrantDeck:** optional and normally unnecessary on OLED; prefer Valve color controls.
- **Fantastic:** optional and normally unnecessary; prefer Valve's fan curve unless measured testing proves a reason to override it.
- **Pause Games:** automatic focus-loss pausing stays off by default because some games react poorly to forced process suspension.

## Commands

```bash
deckctl decky select
deckctl decky selected
deckctl decky install-selected
deckctl decky receipts
deckctl decky plugins
deckctl decky theme install
deckctl decky theme status
deckctl decky css apply
deckctl decky css status
deckctl decky css guide
```

The selector uses KDE `kdialog` checkboxes on SteamOS Desktop Mode and falls back to a terminal selector when `kdialog` is unavailable. Core and Recommended start selected; Optional starts unselected. Every item includes its short what/why blurb.

## CSS component/palette convergence

`Bubble Gum Rave` names the palette in `css-stack.json` and the native
`Bubble Gum Rave - Base` recovery profile. It is not a downloadable theme.
The default selection includes the four Chromahon components, Round, Full Screen
Menus, Colored Keyboard, Centered Game Text, DellyVolume, Better Game Icons,
Better Game Badges, Top Bar Transparency, Better Blur, Better Achievements,
Game Cover Reflections, Percentages, No Game Count, Art Hero, Clean Gameview,
Clean Game Launch, and Focus Highlight Color. Colored Toggles is no longer
installed or included in the managed profile. Existing user-installed copies
are preserved; this release does not delete personal themes.

A component failure is reported by name and the remaining selections are still
attempted. Setup remains CONFIG_REQUIRED until the entire selection verifies.
Completed downloads/configuration are reused on retry.

`deckctl decky css apply` (also `deckctl decky theme install`) performs:

1. Validate the installed CSS Loader identity and native method/loopback contract.
2. Temporarily enable the plugin's documented-in-source `SERVER` sentinel only if
   its local API is unavailable, restarting Decky with normal sudo prompting.
3. Resolve an exact Theme Store name, reject ambiguous/unavailable results, then
   call `download_theme_from_url` with the Store ID and `https://api.deckthemes.com`.
   CSS Loader owns blob downloads and dependency installation. No raw repo cloning.
4. Discover loaded patch options and color-picker components. Use only advertised
   activators and component names. Bright foregrounds, dark panels, and neon focus
   accents use the existing palette. Unsupported unknown controls are reported.
5. Enable components without overwriting dependency colors; verify backend state
   and actual `config_USER.json` or `config_ROOT.json` saved by the plugin.
6. Generate a native profile containing only the managed components, verify its
   dependencies/settings, reload/recheck, and capture it with existing recovery tools.
7. Remove only the temporary sentinel this operation created and restart Decky.

Successful repeated application is a no-op. A receipt is not proof: status checks
actual component manifests, active flags, saved palette values and the native
profile. `verify`/status never enable the bridge or write theme configuration.
UI safe mode blocks reconciliation until explicitly restored. An unchanged legacy
v0.2.18 standalone theme is quarantined under the deckctl state directory; edited
legacy content is preserved and reported. Existing native profiles are backed up
before regeneration. CSS capture/restore and post-update recovery remain available.

The bridge contract is checked from the installed source. A plugin update that
removes methods or changes the bridge is a real `CONFIG_REQUIRED` condition,
not a fabricated success. Retry after resolving the reported problem with
`deckctl decky css apply`. Internet is required only for missing Store components.

## Artwork ownership

SteamGridDB remains a core default plugin and owns Gaming Mode covers, hero images,
logos and icons. “SteamDeckDB” is recorded as the requested artwork alias for this
existing plugin; the official plugin database has no separate entry under that name.
Desktop shortcut icons are owned by `lib/deckctl/desktop.py`, not by CSS Loader or a
second Steam artwork manager.

## Permissions

`deckctl decky install-selected` normally writes plugins as the `deck` user. If `~/homebrew/plugins` is unexpectedly non-writable, deckctl requests sudo only to repair that directory's ownership/write permission, then continues unprivileged. It does not run the whole provisioning system as root and does not recursively change Decky's service directory.

## Desktop Mode vs Game Mode

Run selection, installation, CSS reconciliation and audits in Desktop Mode (guided
setup invokes them there). In Game Mode, use Decky normally and visually check the
configured menus. No shell command or full manual theme checklist is required.

## Upstream contracts used

- [CSS Loader backend](https://github.com/DeckThemes/SDH-CssLoader/blob/main/main.py)
- [Native Theme Store downloads](https://github.com/DeckThemes/SDH-CssLoader/blob/main/css_remoteinstall.py)
- [Patch/component schema](https://github.com/DeckThemes/SDH-CssLoader/blob/main/css_themepatch.py)
- [Profile generation](https://github.com/DeckThemes/SDH-CssLoader/blob/main/css_loader.py)
- [Official Decky plugin database](https://github.com/SteamDeckHomebrew/decky-plugin-database)

Live Store requests returned HTTP 403 in the release-build environment. Automated
integration tests simulate the published backend/storage contract and use extracted
real Chromahon control schemas. Physical SteamOS/Decky visual acceptance is not
claimed by these container tests.

## Installer cleanup

Known staging files are fingerprinted after successful creation. Provisioning
and guided setup remove unchanged installer shortcuts only after the component
verifies. Application launchers, user edits, recovery files and unrelated archives
are retained. Inspect with `deckctl setup cleanup --dry-run`; run
`deckctl setup cleanup` to reconcile an existing Desktop.

## Existing selections in v0.2.25

The five requested plugins (Game Theme Music, Controller Tools, MagicPods,
Bluetooth and TabMaster) are added once to selections from manifest revisions
before 5. Other selections and plugin settings remain intact. Status shows the
effective desired set without writing. Installation commits the selection upgrade
only after confirmation (or `--yes`); dry runs and cancellation do not commit it.
`deckctl decky select` saves the current revision, so deselections stay deselected
on subsequent installs. Already valid plugins are skipped; Store failures remain
visible and retryable. No plugins are automatically removed.

Names and folder IDs were checked against the official Decky plugin database and
upstream plugin.json files:

- [Game Theme Music](https://github.com/MegalonVII/SDH-GameThemeMusic)
- [Controller Tools](https://github.com/jfernandez/ControllerTools)
- [MagicPods](https://github.com/steam3d/MagicPodsDecky)
- [Bluetooth](https://github.com/Outpox/Bluetooth)
- [TabMaster](https://github.com/Tormak9970/TabMaster)

These are install-only additions. Pair devices and choose personal music/tab
preferences through their normal interfaces; provisioning does not overwrite
those settings. Audio Loader remains available alongside Game Theme Music.

Selecting CSS Loader also exposes **CSS components**: choose any subset of the curated theme components, including optional layouts, or clear all to install only the plugin. Apply and verification use that exact selection. Existing themes remain installed and retain their settings when deselected; disable any previously enabled themes in CSS Loader if desired. Additional Store themes and individual style controls remain available in CSS Loader itself.
