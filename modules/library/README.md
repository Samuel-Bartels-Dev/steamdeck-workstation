# Steam library / artwork auditor

Audits managed non-Steam shortcuts and custom-artwork slots without downloading arbitrary artwork automatically.

`deckctl library audit` checks:
- known managed shortcuts (media entries plus registered games),
- whether each shortcut exists in Steam,
- custom grid/capsule/hero/logo/icon files where the shortcut AppID can be resolved.

Use the **SteamGridDB Decky plugin** to fix missing artwork from Game Mode. It supports non-Steam shortcuts and local files.

## v0.2.26 operations

See [Provisioning and recovery](../../docs/OPERATIONS.md) for detailed commands,
verification, failure handling and rollback behavior. Use `deckctl help` for the
complete command reference.
