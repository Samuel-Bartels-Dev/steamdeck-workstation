# Media Apps

Installs **VLC**, **Plex Desktop** (the playback client, not Plex Media Server),
and **Spotify** as user Flatpaks from Flathub:

- [VLC](https://flathub.org/apps/org.videolan.VLC): `org.videolan.VLC` (community package).
- [Plex Desktop](https://flathub.org/apps/tv.plex.PlexDesktop): `tv.plex.PlexDesktop`.
- [Spotify](https://flathub.org/apps/com.spotify.Client): `com.spotify.Client` (community package).

Launch these apps from the Desktop Mode application menu. Existing user/system
Flatpaks are reused, and verification lists missing apps. Plex/Spotify account
sign-in, server selection and subscription features stay inside the apps; an
installed package does not prove login or playback. These native desktop apps
do not replace the optional Chrome-backed Game Mode shortcuts below.

Optional Steam Game Mode web-app shortcuts for Netflix, Hulu, Crunchyroll, and Prime Video.

## Design

Chrome is the single browser runtime. Each service gets:

- a persistent runner under `~/.local/share/deckctl/media/bin/`;
- a standard desktop entry under `~/.local/share/applications/`;
- a non-Steam shortcut submitted through SteamOS' `steamos-add-to-steam` helper, with a Steam URI fallback.

Each shortcut launches desktop Chrome with `--kiosk <service-url>` using Chrome's normal persistent profile. Kiosk mode removes the browser chrome for a cleaner one-site Game Mode experience; it is not a ChromeOS managed-kiosk session and does not intentionally disable normal profile extensions.

KeeperFill is supported as an optional Chrome extension. Install/unlock Keeper once in Desktop Mode; when a matching record exists, Keeper can offer/fill credentials on Netflix, Hulu, Crunchyroll, and Prime Video inside the kiosk page. The extension toolbar itself is hidden in kiosk mode, so keep the vault unlocked for the smoothest Game Mode flow. `deckctl` never stores Keeper credentials, Chrome cookies, or browser profile data.

## Reconciliation

`deckctl media setup` is safe to rerun. Existing Steam shortcuts are detected by name before new ones are submitted, reducing duplicate entries.

`deckctl media status` distinguishes a local launcher from a shortcut actually present in Steam. A staged setup file alone is never considered complete.

## Controls

Recommended baseline for these browser-backed shortcuts:

- right trackpad: mouse;
- trackpad click or R2: left click;
- left trackpad: scroll;
- touchscreen: direct touch;
- `STEAM + X`: keyboard.

Steam Input profile automation is kept separate from media installation so a Steam client/controller-layout change cannot break service provisioning.

## Reconciliation behavior

During initial Desktop Mode provisioning, `deckctl media setup` runs inline and returns when the four local kiosk launchers have been created and submitted to Steam. Steam may not rewrite `shortcuts.vdf` immediately while the client is already running; this is a normal `PENDING STEAM REFRESH` state, not an install failure. Per-service submission receipts prevent repeated submissions/duplicate shortcuts. Switching to Game Mode naturally refreshes Steam. Media setup never invokes BIOS, firmware, or system-update workflows.

## Desktop icons

Distinct bundled SVG icons are installed locally and applied to known project
shortcuts. Media/workspace launchers are also copied to the Desktop. Repair with
`deckctl desktop apply`; audit with `deckctl desktop status`. No Steam Gaming Mode
artwork files are touched; SteamGridDB remains their owner.

## App choices and removal

The desktop Flatpaks in this module are selectable with `deckctl apps select`.
Only selected apps are installed and required by verification; existing apps are
kept when deselected. `deckctl apps uninstall NAME` previews a user-app removal;
add `--yes` to remove it while preserving settings and disabling reinstalls.
See [app management](../../docs/APPS.md). Other module features are independent.
