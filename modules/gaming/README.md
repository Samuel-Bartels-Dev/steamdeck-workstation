# Gaming Module
Steam Game Mode is the primary front end.

## Heroic
Use the Heroic Flatpak in Desktop Mode for Epic/GOG/Amazon install/update/configuration. Enable **Add games to Steam automatically**. Launch once in Desktop Mode if account-linking UI is required; afterward launch the individual game from Steam Game Mode.

## Battle.net / WoW
Guided setup invokes NonSteamLaunchers with the supported `"Battle.net"` command-line argument, so choosing Battle.net installs only Battle.net instead of opening the full launcher checklist. The generic NonSteamLaunchers desktop launcher remains staged only as an advanced/manual fallback for installing other launchers. Completion is verified from the real Battle.net executable in Steam compatdata, never from the staged helper. Keep launcher/prefix state internal by default and prefer internal NVMe for WoW. Consider ConsolePort for WoW controller play. Back up `WTF/` and `Interface/AddOns/`.

## Proton
ProtonPlus is installed for compatibility-tool management. Do not force GE-Proton globally; select it per-title when needed.
