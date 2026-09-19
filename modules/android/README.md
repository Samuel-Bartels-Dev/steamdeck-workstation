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

## Installer cleanup

Known staging files are fingerprinted after successful creation. Provisioning
and guided setup remove unchanged installer shortcuts only after the component
verifies. Application launchers, user edits, recovery files and unrelated archives
are retained. Inspect with `deckctl setup cleanup --dry-run`; run
`deckctl setup cleanup` to reconcile an existing Desktop.
