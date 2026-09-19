# ADR-008 — Media services as browser-backed Steam shortcuts

## Status
Accepted.

## Context
Netflix, Hulu, Crunchyroll, and Prime Video do not need privileged host integration or launcher-specific Wine prefixes on SteamOS. The user wants each service directly available from Steam Game Mode.

## Decision
Use Google Chrome Flatpak as the shared media runtime and create one fullscreen browser launcher per selected service. Add launchers to Steam with SteamOS `steamos-add-to-steam` when available. Keep the entire media capability optional.

## Consequences

- Steam remains the visible front door.
- Only one browser runtime is maintained.
- Provider authentication and DRM remain inside the browser.
- No provider password/token is stored in the repository or `deckctl` state.
- Playback/offline-download behavior is limited by each provider's browser/Linux support.
- SteamGridDB artwork and Steam Input configuration are presentation/input enhancements rather than hard dependencies.


## Password manager

KeeperFill is optional. Media shortcuts use desktop Chrome `--kiosk` with the normal persistent profile rather than ChromeOS managed kiosk mode, so profile extensions can participate in the web page. Keeper installation/sign-in remains interactive and credentials/browser state are outside deckctl desired state and backups.
