# Sunshine Windows host kit

The Steam Deck provisioning path and the Windows host path are deliberately separate.

- Deck: `install.sh` / `deckctl` installs Moonlight, Tailscale client-side support and remote diagnostics.
- Windows gaming PC: `host/windows/Setup-SunshineHost.ps1` prepares/checks Sunshine, optional Tailscale and Wake-on-LAN prerequisites.
- `deckctl remote host-kit NAME` packages `host/windows/` plus a `host.json` containing the registered host's target/MAC/port.

The Deck's `install.sh` **never executes Windows host scripts**.
