# Storage Module

- Internal NVMe: stateful/performance-sensitive workloads, prefixes/caches, WoW, active demanding titles, dev environment.
- `DECK-GAMES`: bulk PC game payloads.
- `DECK-EMU`: EmuDeck ROM/BIOS/emulation library payloads.

Use labels/UUIDs, never a hard-coded mount path.

## EmuDeck migration

`deckctl storage migrate-emulation` validates that `DECK-EMU` is mounted, writes a migration guide, and launches EmuDeck so its **supported Migrate Installation** workflow performs the actual move/reconfiguration. The original internal installation is intentionally preserved until verification.

`deckctl storage finalize-emulation-migration --yes` never deletes the old copy: after target validation it renames the internal source to a timestamped rollback folder for later manual deletion.

## v0.2.27 operations

See [Provisioning and recovery](../../docs/OPERATIONS.md) for detailed commands,
verification, failure handling and rollback behavior. Use `deckctl help` for the
complete command reference.
