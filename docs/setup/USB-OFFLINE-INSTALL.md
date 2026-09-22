# USB delivery — v0.2.40

Extract `STEAMDECK-SETUP-v0.2.40.zip`. The established wrapper contains:

- `STEAMDECK-SETUP/README-FIRST.txt`
- `STEAMDECK-SETUP/INSTALL.sh`
- `STEAMDECK-SETUP/steamdeck-workstation-v0.2.40.tar.gz`
- `STEAMDECK-SETUP/SHA256SUMS` (nested repo checksum)

In Desktop Mode, open Konsole in that folder and run `bash INSTALL.sh` as the normal
Deck user. It verifies the nested checksum, extracts a clean repo with executable
permissions, then runs the normal installer. The normal installer keeps a persistent
copy and `deckctl` command before guided provisioning. Using `bash` also works on
FAT/exFAT USB media that cannot retain Unix executable bits.

The separate `steamdeck-workstation-v0.2.40-SHA256SUMS.txt` verifies the two delivered
archives. Use `sha256sum --check steamdeck-workstation-v0.2.40-SHA256SUMS.txt` with
both archives in the same directory.

Internet remains required for external packages and vendor downloads. This USB
bundle does not contain a full offline dependency cache. Private BIOS/ROM/restore
payloads are never included. If needed, keep them separately on your own media.

Build both release packages with `./tools/build-release /path/to/output`.
Validate extracted copies using `./bin/deckctl repo validate`.
