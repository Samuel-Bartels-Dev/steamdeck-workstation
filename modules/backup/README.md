# Backup / restore module

Protects irreplaceable state rather than replaceable game payloads.

`deckctl backup saves` creates a **v2 manifest-backed archive** containing whichever of these currently exist:
- EmuDeck saves and storage/state,
- WoW WTF / AddOns,
- deckctl configuration and desired state,
- captured/controller templates,
- Steam custom artwork for the active user.

Symlink-backed emulator save locations are dereferenced so the actual data is archived.

`deckctl restore [ARCHIVE]` is a selective restore wizard. It restores emulation data to the **current** EmuDeck location (internal or `DECK-EMU`) instead of assuming the old mount path still exists.

Game payloads, ROM libraries, BIOS downloads, credentials, browser profiles, and tokens are not intentionally backed up by this module.

## v0.2.27 operations

See [Provisioning and recovery](../../docs/OPERATIONS.md) for detailed commands,
verification, failure handling and rollback behavior. Use `deckctl help` for the
complete command reference.
