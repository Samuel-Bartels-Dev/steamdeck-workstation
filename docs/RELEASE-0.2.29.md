# v0.2.29 — More desktop apps

The workstation installer now includes:

- Utilities: Zen Browser (`app.zen_browser.zen`).
- Development: Zed (`dev.zed.Zed`).
- Media: VLC (`org.videolan.VLC`), Plex Desktop (`tv.plex.PlexDesktop`) and Spotify (`com.spotify.Client`).

Apps install from Flathub for the current user and appear in the desktop application menu. Plex is the playback client. VLC, Zed and Spotify packages are community maintained. Account login and playback are separate from package verification. Existing streaming web shortcuts and browser choices are preserved.

Run the normal bootstrap to upgrade and install missing apps. Existing packages are skipped; failed installs are reported and can be retried. A control-plane-only `deckctl update apply` upgrades the installer but does not provision apps by itself.

Repository validation includes isolated installation, repeat-run, missing-app and partial-failure recovery tests. Release packaging validates independent tar and USB extractions. Live package installation was checked on the OLED Deck; application login and media playback were not tested.

The Docker repair, aliases and readiness improvements from [v0.2.28](RELEASE-0.2.28.md) remain included. See the [Docker guide](DOCKER.md).
