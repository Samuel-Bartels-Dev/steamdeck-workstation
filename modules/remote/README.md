# Remote module

Use `deckctl setup customize` to choose individual tools in this category. Selections are saved in `~/.config/deckctl/components.json` and govern installation, verification, and guided setup. Deselecting a tool preserves existing installations and personal settings. Older setups without saved component choices retain their previous defaults.

Moonlight is the PC streaming client; Sunshine runs on home gaming PCs. Tailscale provides private reachability and **must use the SteamOS-specific `tailscale-dev/deck-tailscale` installation path**, not Discover/Flatpak, generic Arch `pacman`, or the normal Linux install script. The guided setup stages `Install-Tailscale.desktop`, which downloads the maintained upstream installer, installs the persistent system service, and then prompts for QR authentication.

After installation, the helper adds a managed, idempotent Bash startup block that loads `/etc/profile.d/tailscale.sh` for interactive terminals. New Konsole/Ghostty Bash sessions can run `tailscale` without manually sourcing the profile file. Existing `.bashrc` content and symlinks are preserved.

chiaki-ng provides PS4/PS5 Remote Play. Use PSN remote mode normally and test it away from home before travel.

Register your home PC with `deckctl remote register desktop --target <tailscale-name-or-IP>`, then run `deckctl remote test desktop` from the hotel or a phone hotspot. It reports the latest Tailscale path (direct or relay), five reply samples, average latency, spread, missed replies, Sunshine TCP reachability, and a conservative Moonlight starting preset. The preset is an estimate: these probes cannot measure sustained bandwidth, video decoding, or hotel congestion. Check Moonlight's streaming statistics while playing and lower bitrate if frames drop. `deckctl remote wake` supports local WoL or an SSH relay on an always-on home node.

## Windows host companion

The repo also contains `host/windows/`. This code is not part of Deck provisioning and is never invoked by `install.sh`. Generate a host-specific Windows ZIP with `deckctl remote host-kit NAME`, or pull the repo on the PC and run `host/windows/Setup-SunshineHost.ps1` directly.

## Installer cleanup

Known staging files are fingerprinted after successful creation. Provisioning
and guided setup remove unchanged installer shortcuts only after the component
verifies. Application launchers, user edits, recovery files and unrelated archives
are retained. Inspect with `deckctl setup cleanup --dry-run`; run
`deckctl setup cleanup` to reconcile an existing Desktop.

The setup UI installs Tailscale inline using a KDE administrator password dialog.
It opens the Tailscale login URL in the default browser without saving that URL
in installer logs. After sign-in, choose Retry or Resume in setup to verify the
connection. Existing connected installations are reused. Terminal setup remains
available for users who explicitly run the command-line helper.

## Parsec

Choose Parsec under **Remote & storage**, or run `deckctl apps install parsec`.
The [community Flathub package](https://flathub.org/en/apps/com.parsecgaming.parsec)
installs in user space. Parsec on Linux is a client for connecting to Windows or
macOS hosts; sign in with your Parsec account from the app menu. Selecting it
does not select Moonlight, chiaki-ng or Tailscale in the setup window.
Verification checks installation; test sign-in and streaming on your own host.

Tailscale readiness checks the installed CLI's backend state. A binary alone is
not proof of login or a running connection. Connected instances are reused;
DNS health warnings remain visible. No peer details or login URLs are saved by
this probe. The upstream helper also skips downloads/login when already connected.
SteamOS resolver configuration is not automatically rewritten. See the
[upstream Linux DNS guidance](https://tailscale.com/docs/reference/linux-dns)
when Tailscale reports a MagicDNS warning.
