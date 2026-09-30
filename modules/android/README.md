# Android Gaming

## Purpose

Provide a SteamOS-aware Android gaming environment for titles such as Pokémon Champions without treating SteamOS like a general Arch workstation.

## Provider

The supported v0.1.2 path is the independently maintained `pjohno/steamos-waydroid-bundle` installer. It builds/installs host components matched to the running SteamOS userspace and keeps persistent Android state under the deck user's home directory.

## Pokémon Champions profile

Use the normal **Android 13 with Google Play** installation. The provider's Android 13 path installs ARM translation plus its Google/Widevine/fingerprint extras. Pokémon Champions is currently distributed as an ARM64 Android application and requires Android 13 or newer.

After Waydroid is installed:

1. Allow the upstream installer to create its Steam shortcut.
2. Provisioning opens `~/Android_Waydroid/Android_Waydroid_Cage.sh` automatically
   when an image exists but Android user state is missing. This launcher mounts
   the custom image before opening Android; do not use the generic Initialize
   Waydroid dialog to download a second image.
3. Sign into Google Play.
4. Close Android to let provisioning check readiness and continue. Install
   Pokémon Champions from Google Play when ready.
5. Link the same Nintendo Account you use elsewhere if you want supported cross-save.
6. Test controller/touch mapping before relying on it while traveling.

### Recommended Deck input profile

Pokémon Champions mobile is touch-oriented outside battles. Keep the Deck touchscreen available and use a Steam Input fallback such as **right trackpad = mouse** with **trackpad click or R2 = left click** for menu navigation. Community reports indicate controller input works more naturally during battles than in the surrounding menus. Do not globally force this mapping onto unrelated Android apps.

## SteamOS updates

Waydroid host integration is more invasive than Flatpaks and can require repair after an atomic SteamOS update. The upstream installer is designed to detect an existing Android image and perform protected host repair without replacing Android apps/login state. `deckctl doctor android` reports the recovery command.

## Ownership and safety

- `deckctl` owns staging, guidance and health detection.
- The upstream Waydroid installer owns privileged host integration and Android image creation/repair.
- Do not bypass compatibility/fingerprint checks.
- Do not use mismatched Waydroid bundles simply to force installation.
- Android app compatibility is not guaranteed; Pokémon Champions is not officially supported on SteamOS.

## State

Important Android state lives primarily under:

- `~/Android_Waydroid/`
- `~/.local/share/waydroid/`

Do not delete those during a normal host repair.

## First-run recovery

`deckctl android retry` skips READY installations, opens the existing bundled
launcher when first-run state is missing, and uses protected host repair only
when that launcher is absent. `deckctl android repair` remains the explicit
post-SteamOS-update repair. Both preserve the image and existing Android data.
The staged Desktop setup shortcut uses the same deckctl path.

The launcher stays in the foreground so sudo and vendor error dialogs remain
visible. Close Android when finished to resume the installer. A nonzero launcher
exit or still-missing user state does not count as successful provisioning.
Headless sessions report CONFIG_REQUIRED and request Desktop Mode.
READY verifies image plus user-state presence; the recommendation line does not
claim to detect the installed Android version or Google account authentication.

## Setup app execution

Install, Retry and Resume execute `android retry` through the existing queue.
Provider stdout/stderr, its redirected installation log, launcher diagnostics,
errors and final verification appear in the shared console. Follow the visible
Android-image chooser and Google Play windows, then close Android to resume
verification. A launcher exit alone never establishes readiness. Healthy images
and user state are reused; missing first-run state opens the existing launcher;
missing launchers use upstream protected host repair. Reinstallation remains an
explicit command, outside the normal retry path.

The app uses a temporary adapter for provider commit
`6f643fb42afc0595a7c8fe1d6f3350b748c8001c`. SHA-256 checks pin the installer,
authentication function and launcher contracts being adapted. Unknown versions
stop with CONFIG_REQUIRED and a review message. The launcher source is checked
before provider execution as well as before launching. The original checkout is
preserved. Compatibility, bundle/fingerprint, storage, protected-repair and
image selection checks execute as upstream supplied them.
The installed Toolbox records the original checkout as its recovery source,
so it never points at a removed temporary adapter.

The adapter replaces only the stdin password prompt and its `sudo -S -k -v`
validation with app-owned sudo validation. Its password variable is empty; no
password is supplied to the provider. The scoped sudo shim rejects invalidation
and unknown policy flags. The provider's four runtime sudoers entries retain their
exact command restrictions but use PASSWD in the temporary copy, so this path
adds no persistent NOPASSWD rules. Existing rules and installations are not
removed. Terminal CLI behavior remains upstream's interactive path.

App provisioning keeps the existing Steam shortcut target usable after setup
closes. It saves the exact inspected vendor launcher as
`~/Android_Waydroid/Android_Waydroid_Cage.vendor.sh` and installs a small wrapper
at the original launcher path. The wrapper opens the same foreground Android
session with temporary KDE administrator authorization, then invalidates that
authorization when Android closes. Each durable launch creates its own owner and
discards inherited setup sockets, sudo shim paths and queue-control variables.
It preserves package arguments and does not
store passwords. Edited vendor scripts and unrelated recovery files are refused
and preserved. The wrapper pins the immutable installed release that created it
under `~/.local/share/steamdeck-workstation/releases/`, so changing or rolling
back `current` does not send Android into an older runtime without launch support.
Missing release files or launch capability produce CONFIG_REQUIRED; activate the
reviewed release with `install.sh` and Retry. A retry can migrate an exact known
older generated wrapper, including the former `current/lib` wrapper, while
preserving vendor bytes and refusing custom edits. Temporary adapters and
development checkouts are refused as durable launch targets.

The temporary launcher adapter also changes the inspected resolution pipeline
to drain all `xdpyinfo` output while retaining its first dimensions result.
This prevents an early `awk` exit from causing SIGPIPE/status 141 under `pipefail`;
real display-command failures still fail. The original vendor launcher, image,
apps and login state remain untouched by this adaptation.

Controller helpers started by the inspected vendor runtime are supervised for
the Android session, rather than killed when its startup command returns. Their
lease is released when Android closes, including when the setup window remains
open. Closing or losing the standalone launcher also stops its foreground GUI
and supervised privileged helpers.

In Nested Desktop, incomplete Android work is deferred before authorization,
downloads or provider execution because the provider can stop/restart Decky.
Healthy Android items are reused, and independent user-space installs continue.
Switch manually to normal Desktop Mode before Retry; setup never switches sessions.

## Installer cleanup

Known staging files are fingerprinted after successful creation. Provisioning
and guided setup remove unchanged installer shortcuts only after the component
verifies. Application launchers, user edits, recovery files and unrelated archives
are retained. Inspect with `deckctl setup cleanup --dry-run`; run
`deckctl setup cleanup` to reconcile an existing Desktop.
