# Recovery

Keep a known-good release archive and its checksum on a USB drive, NAS, or another trusted location. Delivery method must not change provisioning behavior.

Recovery priorities:
1. SteamOS/Valve recovery if the OS itself is damaged.
2. Re-obtain a known-good `steamdeck-workstation` release.
3. Run `install.sh` / `deckctl apply` to recreate software/configuration.
4. Restore saves and selected personal state from versioned backup.
5. Re-authenticate services manually.
6. Run `deckctl verify`.

Do not rely on a raw clone of the old Deck. Reprovision known desired state, then restore personal state.
