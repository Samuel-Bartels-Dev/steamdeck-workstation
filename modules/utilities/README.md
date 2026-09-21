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

## Chat apps

Discord (`com.discordapp.Discord`) and Slack (`com.slack.Slack`) are available
through user Flathub installs. Choose them in the installer or run
`deckctl apps install discord slack`. Existing saved selections are preserved;
new catalog entries are not silently added to a saved selection. Login, calls,
screen sharing and workspace access require configuration and testing in each app.

Telegram and WhatsApp are also independent choices:
`deckctl apps install telegram whatsapp`.
[Telegram](https://flathub.org/en/apps/org.telegram.desktop) uses its desktop client.
[Whatsie](https://flathub.org/en/apps/com.ktechpit.whatsie) is a third-party
WhatsApp Web client, labeled **WhatsApp (Whatsie)** in the chooser. Link your
phone in the app; deckctl does not collect login information.
