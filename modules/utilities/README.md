# Utilities

Installs low-risk troubleshooting utilities that support the managed Deck. v0.2.0 includes **Flatseal** so filesystem/device permissions for Flatpak apps can be inspected when Heroic, Chrome, Moonlight, etc. cannot see removable storage or devices.

Also installs **Zen Browser** (`app.zen_browser.zen`) from Flathub as a user app,
following [Zen's Linux installation guide](https://docs.zen-browser.app/guides/install-linux).
It does not replace the default browser or Chrome's existing kiosk workflows.
Existing user/system Flatpak installations are reused. Missing apps are reported
by verification and failed downloads remain retryable through `deckctl apply`.

## App choices and removal

The desktop Flatpaks in this module are selectable with `deckctl apps select`.
Only selected apps are installed and required by verification; existing apps are
kept when deselected. `deckctl apps uninstall NAME` previews a user-app removal;
add `--yes` to remove it while preserving settings and disabling reinstalls.
See [app management](../../docs/APPS.md). Other module features are independent.
