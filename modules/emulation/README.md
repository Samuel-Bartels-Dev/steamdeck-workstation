# Emulation Module
EmuDeck owns emulator defaults. This project owns provisioning guidance, storage roles, validation, backup policy, and targeted overrides.

Prefer the Emulation tree on `DECK-EMU`; use ES-DE for the full library and Steam ROM Manager for favorites/current titles. BIOS/firmware and ROM content are private inputs and never belong in Git. Some systems use `Emulation/bios`; others install firmware through emulator UI. Run EmuDeck's BIOS checker.

Do not restore stale global emulator configs over a fresh EmuDeck install; preserve saves/per-game overrides and let EmuDeck own general defaults.

## Installer cleanup

Known staging files are fingerprinted after successful creation. Provisioning
and guided setup remove unchanged installer shortcuts only after the component
verifies. Application launchers, user edits, recovery files and unrelated archives
are retained. Inspect with `deckctl setup cleanup --dry-run`; run
`deckctl setup cleanup` to reconcile an existing Desktop.

EmuDeck completion requires the executable `~/Applications/EmuDeck.AppImage`,
the vendor `.finished` and `.ui-finished` markers under `~/.config/EmuDeck`,
and no active `install.pid` marker. A bare Emulation folder is insufficient.
Verified installs skip bootstrap staging and launch prompts. Exact copies of the
legacy official downloader on the Desktop are recognized, while the EmuDeck
management application shortcut remains available. Vendor marker references:
[setup script](https://github.com/dragoonDorise/EmuDeck/blob/main/setup.sh) and
[bootstrap](https://github.com/dragoonDorise/EmuDeck/blob/main/install.sh).
