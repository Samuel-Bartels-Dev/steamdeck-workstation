# Steam Deck Workstation — v0.2.31

Desktop apps include Zen Browser, Zed editor, VLC, Plex Desktop and Spotify, installed through Flathub. Existing installations are reused; account setup remains inside each app. See the [Docker guide](docs/DOCKER.md) for the included container tooling.

## Copy/paste quick fixes

```bash
deckctl -h
dhealth
dandroid
dandroidretry
dworkspace
```

### Android / Waydroid

If the Android wizard ran but Android never actually appeared:

```bash
deckctl android status
deckctl android retry
# If Android is installed but Steam has not refreshed the shortcut yet,
# status reports PENDING_STEAM_REFRESH; do not reinstall just for that.
```

For a fresh install, choose **Android 13 with Google Play**. The setup step is only READY when both the persistent Waydroid image and Android user-state directory exist.

After a SteamOS update or if host integration breaks while Android data still exists:

```bash
deckctl android repair
```

To deliberately rebuild Android itself:

```bash
deckctl android reinstall
```

### Notion / ChatGPT / Claude

```bash
deckctl workspace setup
deckctl workspace status
deckctl workspace notion-mcp
```

These are clean Chrome app-window shortcuts on SteamOS. Notion MCP is the recommended path for allowing an authorized ChatGPT/Codex/Claude client to read and write your Notion workspace.

Repeatable SteamOS provisioning for a Steam Deck used as a gaming handheld, emulation console, Android device, media handheld, remote-gaming thin client, and lightweight development workstation.

> **Start here:** this README is intentionally copy/paste-first. Pick the situation you are in, run the block, then use the deeper reference sections below.

## 1. Fresh Deck / fresh factory reset

Finish Valve's first-run wizard first: connect Wi-Fi, sign into Steam, install all **Stable** SteamOS updates, reboot, and switch to **Desktop Mode**.

If you copied the release tarball from USB into `~/Downloads`:

```bash
cd ~/Downloads
tar -xzf steamdeck-workstation-v0.2.31.tar.gz
cd steamdeck-workstation-0.2.31
chmod +x install.sh
./install.sh
```

**Do not run `sudo ./install.sh`.** Provisioning runs as the normal `deck` user and asks for sudo only when a narrow operation genuinely requires it.

The installer creates a persistent control-plane copy under:

```text
~/.local/share/steamdeck-workstation/
```

and installs the permanent command at:

```text
~/.local/bin/deckctl
```

When the installer finishes, open a new Konsole window or run:

```bash
source ~/.config/deckctl/shell/aliases.sh
```

Then verify the Deck:

```bash
dhealth
dverify
dstatus
```

Before wiping an existing Deck, read [`docs/setup/PRE-WIPE.md`](docs/setup/PRE-WIPE.md). The full clean-install walkthrough is [`docs/setup/NEW-DECK.md`](docs/setup/NEW-DECK.md).

---

## 2. Upgrade / reconcile an already configured Deck

You do **not** need to wipe or start over. Extract the new release into a new folder and run its installer:

```bash
cd ~/Downloads
tar -xzf steamdeck-workstation-v0.2.31.tar.gz
cd steamdeck-workstation-0.2.31
chmod +x install.sh
./install.sh
```

`deckctl` reconciles desired state: healthy completed items are skipped, missing/new items are offered or applied, and interactive items remain resumable.

Afterward:

```bash
source ~/.config/deckctl/shell/aliases.sh
dhealth
dverify
```

---

## 3. Resume an interrupted guided setup

See what is complete, missing, or stale:

```bash
~/.local/bin/deckctl setup status
```

Resume from the next required step:

```bash
~/.local/bin/deckctl setup run
```

After aliases are loaded, the same commands are:

```bash
dstatus
dsetup
```

If one guided action failed, fix that component and run `dsetup` again. The setup runner re-detects completed state rather than assuming a previous click succeeded.

---

## 4. Decky plugins: select, install, verify

> **Run all `deckctl ...` commands in Desktop Mode/Konsole.** Game Mode does not natively provide the shell used by `deckctl`. Guided setup completes the command-line work before asking you to return to Game Mode.


Open the three-section checkbox selector (**Core / Recommended / Optional**):

```bash
dpluginselect
```

Automatically install the missing plugins you selected from Decky's published Plugin Store artifacts:

```bash
dplugininstall
```

Audit desired vs actually installed:

```bash
dplugins
```

Preview without changing anything:

```bash
deckctl decky install-selected --dry-run
```

If a selected artifact cannot be safely resolved or validated, `deckctl` leaves it missing and tells you to install that item through Decky's normal Plugin Store instead of forcing it.

### Bubble Gum Rave palette

Guided setup installs CSS Loader through the existing Decky Store installer. It then
uses **CSS Loader's native Theme Store download mechanism** to obtain the four
Chromahon components and the existing recommended polish set, including
DellyVolume, Focus Highlight Color, and Colored Keyboard. The default selection also
includes Percentages, Round, Clean Gameview, Centered Game Text, Art Hero, Better Blur,
Better Game Badges, Better Achievements, Clean Game Launch, and Game Cover Reflections.

**Bubble Gum Rave is a palette, not a standalone theme.** The installer discovers
supported color controls, applies the dark pink/violet/cyan palette, verifies live
and persisted settings, and creates/captures a native `Bubble Gum Rave - Base`
profile. Components without color controls retain their defaults. Optional layout
components remain opt-in. No GitHub theme cloning or alternate artwork downloader
is used.

Normal setup handles this automatically in Desktop Mode. Repair/audit commands:

```bash
deckctl decky css apply
deckctl decky css status
deckctl decky css capture
```

The older `deckctl decky theme install` and `dtheme` commands remain compatible.
An exact v0.2.18 standalone theme is moved to a recovery backup before applying the
new palette. A locally edited old theme is preserved and reported for review.
Unavailable Store items or incompatible plugin APIs return `CONFIG_REQUIRED`, with
a retry command; they never count as configured.

### Desktop icons and Gaming Mode artwork

Media and workspace app launchers now have distinct bundled SVG icons and Desktop
copies. `deckctl desktop apply` repairs them; `deckctl desktop status` audits them.
Only known project shortcuts are touched. **SteamGridDB owns Gaming Mode artwork**;
this Desktop operation never reads or writes Steam grid artwork or `shortcuts.vdf`.
The artwork request called “SteamDeckDB” maps to the existing SteamGridDB plugin,
which remains selected by default. No second plugin identity is invented.

### Decky

> **State rule:** Decky selection state is stored only in `~/.config/deckctl/decky-selection.json`. Desktop `.txt` checklists are not created and are never accepted as proof that Decky or a plugin is installed. `dplugins` verifies the real Loader and real plugin folders.
 permission repair

Normally `~/homebrew/plugins` belongs to the `deck` user. If it is unexpectedly not writable, `deckctl` requests sudo only to repair that narrow plugin-directory ownership/permission boundary, then continues as the normal user.

Do **not** solve this by running all of `deckctl` as root.

---

## 5. Controller templates

Install/copy the repo-owned templates:

```bash
dcontroller
deckctl controller install-templates
```

If you are still inside the initial setup and your shell has not refreshed PATH yet, the absolute command always works:

```bash
~/.local/bin/deckctl controller install-templates
```

During the normal guided first-run flow this step runs **inline** and verifies automatically; it no longer opens a second Konsole window. Seeing the destination path means the template copy succeeded. Stay in Desktop Mode and continue setup. When you later switch to Game Mode, Steam reloads and should discover the template. Restart Steam only if the template is still missing after that transition.

Useful controller commands:

```bash
deckctl controller status
deckctl controller recommend "Pokemon Champions"
deckctl controller recommend "PCSX2" --system ps2
deckctl controller discover
deckctl controller capture "My Layout" --source /path/to/layout.vdf
```

`deckctl` does not blindly replace Valve/developer Steam Input layouts. Repo templates are for workflows where we intentionally want a known-good layout, such as media, Android, Moonlight, chiaki-ng, WoW, or emulation.

---

## 6. Emulation now; move to the real SD card later

If your final emulation microSD is not available yet, using internal storage temporarily is supported.

When the real `DECK-EMU` card is ready:

```bash
deckctl storage migration-status
dmigrate
```

`deckctl` preflights the target and hands the actual move to EmuDeck's migration workflow rather than inventing a second migration engine.

After you have verified ROMs, BIOS/firmware, saves, and ES-DE on the new card:

```bash
deckctl storage finalize-emulation-migration
```

The destructive cleanup path is intentionally explicit; the old internal data is retained as rollback state until you choose to remove it.

---

## 7. Media shortcuts

Create/reconcile the Game Mode media entries:

```bash
dmedia
deckctl media setup
```

The target tiles are:

```text
Netflix
Hulu
Crunchyroll
Prime Video
```

The tiles launch Chrome in **true `--kiosk` mode** using the normal persistent Chrome profile, so each service stays clean/fullscreen while normal profile extensions remain available.

Install KeeperFill during guided setup, or manually in Desktop Mode:

```bash
deckctl media keeper setup
dkeeper
```

After you click **Add to Chrome** and sign into/unlock Keeper once, matching Keeper records can autofill Netflix/Hulu/etc. inside their kiosk pages. The Chrome toolbar is hidden in kiosk mode, so the smoothest Game Mode experience is to have Keeper already unlocked; `deckctl` never stores Keeper credentials, cookies, or browser profile data.

---

## 8. Remote gaming / network checks

General network health:

```bash
dnetwork
```

Register a Sunshine PC once you know its Tailscale/DNS target and LAN MAC:

```bash
deckctl remote register gaming-pc \
  --target gaming-pc.tailnet.ts.net \
  --mac AA:BB:CC:DD:EE:FF
```

Test it:

```bash
deckctl remote test gaming-pc
```

Wake it:

```bash
deckctl remote wake gaming-pc
deckctl remote wait gaming-pc
```

### Windows Sunshine host kit

The Windows host helper is versioned in this repo under `host/windows/`, but **Deck `install.sh` never runs it**.

Either pull/copy the repo onto the Windows gaming PC and run the files under `host/windows/`, or generate a host-specific ZIP from the Deck:

```bash
deckctl remote host-kit gaming-pc
```

---

## 9. Backup and restore

Create a save/config backup:

```bash
dbackup
```

Run the restore selector:

```bash
drestore
```

Backups can include emulator saves/state, WoW WTF/AddOns, `deckctl` configuration, controller templates, and Steam custom artwork. ROM libraries and copyrighted BIOS/firmware are intentionally not treated as normal Git-managed data.

---

## 10. Reliability / recovery layer

Capture the exact CSS Loader profiles after you finish tuning `Bubble Gum Rave - Base` and `Bubble Gum Rave - Full`:

```bash
dcsscapture
deckctl decky css profiles
```

Restore the captured profiles after a rebuild/update:

```bash
dcssrestore
```

If a Steam client/UI update breaks the heavier styling, quarantine only the optional/heavy CSS layers:

```bash
duisafe
```

For a harder CSS reset that also quarantines the Base/community layers and saved live profiles:

```bash
deckctl ui safe --minimal
```

Restore what was quarantined:

```bash
duirestore
```

After a SteamOS update, reconcile Decky, selected plugins, Bubble Gum Rave, captured CSS profiles, and controller templates, then run health checks:

```bash
dpostupdate
```

Export portable desired state (no browser/Keeper credentials, cookies, ROMs, BIOS, or private keys):

```bash
dprofileexport
```

Import it on another/rebuilt Deck:

```bash
deckctl profile import ~/DeckExports/deck-profile-YYYYMMDD-HHMMSS.zip
```

Self-update/rollback uses versioned releases. GitHub is configured as the release source. You can also apply a downloaded release archive explicitly:

```bash
deckctl update apply --archive ~/Downloads/steamdeck-workstation-X.Y.Z.tar.gz
drollback
```

Create a sanitized support package for troubleshooting:

```bash
dsupport
```

The support bundle intentionally excludes browser profiles, Keeper data, credentials/tokens, ROMs, BIOS/firmware, private keys, save payloads, and registered remote-host addresses/MACs. Review the ZIP before sharing it.

---

## 11. Terminal / Konsole polish

The terminal layer is installed automatically by the normal provisioning pass. It keeps **Bash** as the default shell and installs everything in user space; no `pacman` mutation is required.

Check it:

```bash
dterminal
```

Apply/repair the full terminal stack:

```bash
dtermapply
```

The managed stack includes:

```text
JetBrainsMono Nerd Font Mono
Starship prompt
zoxide
fzf
eza
bat
fastfetch
tmux persistent terminal multiplexer
Bubble Gum Rave Konsole profile/color scheme
```

Open a **new Konsole window** after installation. The prompt shows a compact current path/PWD, Git branch/status, active Python/Node/Rust/Go context when relevant, battery, time, command duration, and a cyan/red success/error prompt.

Useful shell helpers:

```text
ll       detailed eza listing with Git status/icons
lt       two-level eza tree
cat      bat in interactive shells; falls back to real cat
ff       compact fastfetch
z / zi   zoxide smart cd / interactive picker
Ctrl-R   fuzzy shell history
Ctrl-T   fuzzy files/directories
Alt-C    fuzzy directory jump
c        clear
.. ...   parent directory shortcuts
mkcd     create a directory and enter it
gs       git status -sb
gd       git diff
gl       compact graph log
tm       create/attach persistent tmux session
tml      list tmux sessions
tma      attach/switch tmux session
tmk      kill tmux session after confirmation
tmhelp   tmux split/navigation cheat sheet
```

If Fastfetch ever needs to be repaired or refreshed:

```bash
deckctl terminal apply --refresh
fastfetch --version
ff
```

`ff` is only the convenience shell function; the managed executable is `~/.local/bin/fastfetch`.

Font diagnostic:

```bash
deckctl terminal font-check
```

Return to the stock shell/Konsole presentation if needed:

```bash
dtermreset
```

`dtermreset` only deletes downloaded binaries/fonts if their hashes still match the files that `deckctl` installed. If you have modified/replaced one yourself it is preserved. To remove the presentation but keep the CLI tools:

```bash
deckctl terminal reset --keep-tools
```

The stock Konsole profile remains installed as a fallback even while Bubble Gum Rave is the default.

### Persistent splits with tmux

Konsole still has its own native split-view commands for quick work. For persistent dev/admin work, run:

```bash
tm
```

That creates or reattaches a `main` tmux session. Closing Konsole or detaching does not stop the session. Use `tmhelp` at any time.

```text
Ctrl+A |           split left/right
Ctrl+A -           split top/bottom
Alt+Arrow          move between panes
Ctrl+A H/J/K/L     resize panes
Ctrl+A z           zoom/unzoom pane
Ctrl+A c           new tmux window in current directory
Ctrl+A d           detach and leave session running
Ctrl+A r           reload config
mouse drag border  resize pane
```

Direct management:

```bash
dtermux
deckctl terminal tmux apply
```

tmux is **not** auto-started when Konsole opens; normal shell windows stay normal until you run `tm`.

---

## 12. “Something is wrong” copy/paste block

Start here:

```bash
dhealth
dverify
ddoctor
dstatus
dplugins
dstorage
dnetwork
dterminal
```

If you need a sanitized support package:

```bash
deckctl support-bundle
```

The support bundle is designed not to intentionally collect credentials, ROMs, BIOS binaries, or private keys.

---

## Permanent commands and aliases

After first install, `deckctl` is available from any new terminal. Aliases are generated from the canonical [`config/aliases.json`](config/aliases.json).

```text
dctl            deckctl
dplan           deckctl plan
dapply          deckctl apply
dverify         deckctl verify
dsetup          deckctl setup run
dstatus         deckctl setup status
ddoctor         deckctl doctor
dstorage        deckctl storage health
dlaunchers      deckctl launcher status
dbattlenet      deckctl launcher install battlenet

# Targeted Battle.net install — skips the full NonSteamLaunchers picker
deckctl launcher install battlenet
dmedia          deckctl media status
dtravel         deckctl travel check
dbackup         deckctl backup saves
drestore        deckctl restore
dplugins        deckctl decky plugins
dpluginselect   deckctl decky select
dplugininstall  deckctl decky install-selected
dtheme          deckctl decky theme status
dcss            deckctl decky css status
dcssguide       deckctl decky css guide
dhealth         deckctl health
dnetwork        deckctl network test
dcontroller     deckctl controller status
dlibrary        deckctl library audit
dmigrate        deckctl storage migrate-emulation
dhostkit        deckctl remote host-kit
dcsscapture     deckctl decky css capture
dcssrestore     deckctl decky css restore
duisafe         deckctl ui safe
duirestore      deckctl ui restore
dpostupdate     deckctl post-update
dupdate         deckctl update check
drollback       deckctl update rollback
dprofileexport  deckctl profile export
dsupport        deckctl support-bundle
dkeeper         deckctl media keeper status
dterminal       deckctl terminal status
dtermapply      deckctl terminal apply
dtermreset      deckctl terminal reset
```

Show the live list anytime:

```bash
deckctl aliases
```

---

## Useful command cookbook

### Provisioning / health

```bash
deckctl detect
deckctl plan
deckctl apply
deckctl verify
deckctl doctor
deckctl health
deckctl inventory
deckctl support-bundle
```

### Terminal / Konsole

```bash
deckctl terminal status
deckctl terminal apply
deckctl terminal font-check
deckctl terminal tmux status
deckctl terminal tmux apply
deckctl terminal reset --keep-tools
```

### Storage / games

```bash
deckctl storage health
deckctl storage recommend "World of Warcraft"
deckctl storage recommend "Gran Turismo 4" --system ps2
deckctl game ready "World of Warcraft"
deckctl game doctor "World of Warcraft"
```

### Launchers / media / library

```bash
deckctl launcher status
deckctl media status
deckctl media setup
deckctl media keeper setup
deckctl media keeper status
deckctl library audit
```

### Emulation

```bash
deckctl emulation bios-audit
deckctl emulation bios-import --source /path/to/private/bios
deckctl storage migration-status
deckctl storage migrate-emulation
```

### Remote

```bash
deckctl network test
deckctl remote test gaming-pc
deckctl remote wake gaming-pc
deckctl remote wait gaming-pc
deckctl remote host-kit gaming-pc
```

### Backup / travel

```bash
deckctl backup saves
deckctl restore
deckctl travel check
```

### Repo / update / AI-agent context

```bash
deckctl export
deckctl update check
deckctl update apply --archive /path/to/release.tar.gz
deckctl update rollback
deckctl profile export
deckctl profile import /path/to/deck-profile.zip
deckctl post-update
deckctl ui safe
deckctl ui restore
deckctl support-bundle
deckctl repo validate
deckctl ai context
deckctl ai task
```

---

## What the platform owns

- SteamOS-safe user-space provisioning and reconciliation.
- Hardware/profile detection for OLED/LCD and operational profiles.
- Steam-first launch/presentation model.
- Heroic for Epic/GOG/Amazon management.
- Battle.net/WoW through NonSteamLaunchers targeted `"Battle.net"` CLI install; the full NSL launcher picker is advanced/manual fallback only.
- ProtonPlus for compatibility-tool management.
- Decky desired state, selected-plugin installation/audit, and Bubble Gum Rave.
- EmuDeck/ES-DE integration without overwriting EmuDeck-owned emulator configs wholesale.
- Android/Waydroid integration.
- Tailscale + Moonlight remote access, with chiaki-ng for PlayStation.
- Distrobox/project tooling plus host-level Codex.
- Backup/restore, travel checks, controller templates, artwork auditing, storage migration, and health diagnostics.

## What it deliberately does not own

- Your Steam/media/Google/PSN/Battle.net credentials.
- ROMs or copyrighted BIOS/firmware in Git.
- Global “magic performance tweaks.” PowerTools is per-game/per-emulator unless testing proves otherwise.
- Automatic fan-curve, saturation, undervolt, CryoUtilities-style, or SteamOS base-image mutations.
- Windows Sunshine host execution from Deck `install.sh`.

## Design principles

- SteamOS remains vendor-owned.
- `apply` reconciles desired/current state.
- `verify` is read-only.
- `doctor` may repair known-safe state.
- Disruptive migrations are explicit.
- Interactive/authentication steps are valid `CONFIG_REQUIRED` states, not fake failures.
- Installer presence is not proof of configuration; feature detection/verification decides completion.
- Secrets and private content stay out of source control.

For deeper architecture, testing, security, recovery, and setup notes, see [`docs/`](docs/).

## Release regression guardrails

The contracts that must survive future releases are tracked in [`docs/REGRESSION-MATRIX.md`](docs/REGRESSION-MATRIX.md) and enforced where possible by `deckctl repo validate`.


### Media shortcut note

During Desktop setup, Netflix/Hulu/Crunchyroll/Prime Video are created and submitted once. If Steam has not yet refreshed `shortcuts.vdf`, `dmedia` may show `PENDING STEAM REFRESH`; this is normal. Do not rerun the media installer repeatedly. Switching to Game Mode refreshes Steam.


## Prompt engine (Oh My Posh / Starship)

Oh My Posh is the default Bubble Gum Rave prompt engine. Starship stays installed as a fallback; never enable both at once.

```bash
deckctl terminal prompt status
deckctl terminal prompt use posh
deckctl terminal prompt use starship
```

Aliases: `dposh` and `dstarship`. The local Oh My Posh theme is `~/.config/deckctl/terminal/bubble-gum-rave.omp.json`.

## Command help and engineering review

Every command supports `--help`, including nested commands such as
`deckctl decky css apply --help`. Use `deckctl help decky css apply` for the
same detailed entry, or `man deckctl` after installation.

- [Complete command manual](docs/COMMANDS.md)
- [Installer and maintenance script reference](docs/SCRIPTS.md)
- [v0.2.20 engineering review and limitations](docs/ENGINEERING-REVIEW-0.2.20.md)

Release v0.2.20 adds comprehensive help and targeted reliability fixes while
preserving all v0.2.19 modules and the protected Waydroid implementation.

The manual validation handles Python 3.12/3.13 usage wrapping.

### Updating an existing Deck

Run the normal installer from the new release; a wipe is not required. The
versioned control plane is promoted while the previous release is retained.
Modules reconcile their managed setup and completed guided steps are skipped.
The v0.2.22 preflight fix allows this flow when Decky is already installed.
See [the latest release notes](docs/RELEASE-0.2.31.md).

## Online releases and recovery

See [GitHub distribution](docs/GITHUB-RELEASES.md) for the public source and internet
installer, and [Provisioning and recovery](docs/OPERATIONS.md) for step retries,
upgrade previews, shortcut repairs, restore and verified SD migration.

## Optional Docker/Compose for dashboard development

The normal installer offers an optional Docker development setup. Use
`deckctl containers install` to opt in later, `deckctl containers check` for
rootless SteamOS prerequisites, or `deckctl containers install --remote
ssh://user@host` (on one line) for an existing Linux Docker host over SSH.

Compose and Buildx support beacon/dashboard and RLCS development stacks.
`deckctl containers compose -- up --build -d` runs your own project's Compose
file from its checkout. Local startup is session-only by default; existing
engines, Podman/Distrobox, volumes and databases are preserved. Missing host
prerequisites are reported without unlocking SteamOS.

See [container setup, commands and limitations](modules/dev/containers/README.md).

## Choose or remove desktop apps

The installer offers a desktop app chooser. Revisit it with `deckctl apps select`,
then install your choices with `deckctl apps install`. Use
`deckctl apps uninstall spotify` to preview removal, and append `--yes` to apply
while keeping settings. See [app management](docs/APPS.md).

Discord and Slack are also available: `deckctl apps install discord slack`.
