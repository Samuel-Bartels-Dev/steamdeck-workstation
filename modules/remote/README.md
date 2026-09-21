# Remote module

Use `deckctl setup customize` to choose individual tools in this category. Selections are saved in `~/.config/deckctl/components.json` and govern installation, verification, and guided setup. Deselecting a tool preserves existing installations and personal settings. Older setups without saved component choices retain their previous defaults.

Moonlight is the PC streaming client; Sunshine runs on home gaming PCs. Tailscale provides private reachability and **must use the SteamOS-specific `tailscale-dev/deck-tailscale` installation path**, not Discover/Flatpak, generic Arch `pacman`, or the normal Linux install script. The guided setup stages `Install-Tailscale.desktop`, which downloads the maintained upstream installer, installs the persistent system service, and then prompts for QR authentication.

chiaki-ng provides PS4/PS5 Remote Play. Use PSN remote mode normally and test it away from home before travel.

`deckctl remote test` inspects the Tailscale path and probes Sunshine. `deckctl remote wake` supports local WoL or an SSH relay on an always-on home node.

## Windows host companion

The repo also contains `host/windows/`. This code is not part of Deck provisioning and is never invoked by `install.sh`. Generate a host-specific Windows ZIP with `deckctl remote host-kit NAME`, or pull the repo on the PC and run `host/windows/Setup-SunshineHost.ps1` directly.

## Installer cleanup

Known staging files are fingerprinted after successful creation. Provisioning
and guided setup remove unchanged installer shortcuts only after the component
verifies. Application launchers, user edits, recovery files and unrelated archives
are retained. Inspect with `deckctl setup cleanup --dry-run`; run
`deckctl setup cleanup` to reconcile an existing Desktop.

## Parsec

Choose Parsec under **Desktop apps**, or run `deckctl apps install parsec`.
The [community Flathub package](https://flathub.org/en/apps/com.parsecgaming.parsec)
installs in user space. Parsec on Linux is a client for connecting to Windows or
macOS hosts; sign in with your Parsec account from the app menu. Selecting it
does not select Moonlight, chiaki-ng or Tailscale in the setup window.
Verification checks installation; test sign-in and streaming on your own host.
