PRIVATE BIOS BUNDLE SHAPE (example only — do not put real binaries in Git)

bios/
  generic/   -> files intended for EmuDeck's Emulation/bios directory
  rpcs3/     -> PS3 firmware/packages kept private and installed through RPCS3 UI
  vita3k/    -> Vita firmware kept private and installed through Vita3K UI

Use: deckctl emulation bios-import --source /path/to/private/bios
Only generic/ is copied automatically.
