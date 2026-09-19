# Windows Sunshine host companion kit

This directory is **not executed by Steam Deck `install.sh`**. It is a separate Windows-host deliverable that lives in the same repo so the remote-gaming configuration has one source of truth.

Use either:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\Setup-SunshineHost.ps1
```

or generate a host-specific ZIP from the Deck/repo:

```bash
deckctl remote host-kit gaming-pc
```

The setup script:
- checks for Sunshine, downloads the current official GitHub MSI, and launches it interactively when missing,
- checks for Tailscale and can install it interactively with WinGet,
- reports Sunshine/Tailscale service state,
- reports active physical adapters, MAC addresses and Wake-on-LAN capability,
- does not silently change BIOS, NIC power policy, Sunshine credentials, or paid/optional virtual-HID features.

Sunshine's upstream Windows documentation currently recommends its MSI installer and explicitly cautions users to review installer features rather than blindly enabling everything.
