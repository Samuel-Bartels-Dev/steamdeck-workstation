# Steam Deck release smoke test

This checklist is for maintainers validating a candidate release. It is not an
extra end-user installation procedure. The normal entry point remains
`./install.sh`; provisioning should converge without a manual software checklist.

Use a test Deck or backed-up data. Do not wipe an existing Deck just to fill out
this report. Use separate fresh-install and upgrade test opportunities. Close
apps before recovery tests and use disposable files, not irreplaceable saves.

## Report header

Copy this document into a release PR/issue and fill in:

- Date and candidate version/commit:
- Deck model (LCD/OLED; no serial number):
- SteamOS version, build and channel:
- Steam client version and channel:
- Installation path: fresh / upgrade from version / same-version repeat:
- Distribution: GitHub bootstrap / tar / USB ZIP:
- Relevant vendor/plugin versions:
- Storage: internal / DECK-GAMES / DECK-EMU (no identifying mount paths):
- Overall result and unresolved failures:

Use PASS, FAIL, BLOCKED, NOT TESTED, or NOT APPLICABLE plus evidence for each row.
Blank rows do not mean success. A required check that is blocked or untested
prevents claiming full hardware validation for that scenario.

## Core checks

| Check | Expected observable result | Result / evidence |
| --- | --- | --- |
| Delivery | Published checksums match; archive extracts; installer starts from the extracted folder, including a folder with spaces. | NOT TESTED |
| Fresh setup | On an available clean test Deck, normal installer proceeds from prechecks into provisioning. Authentication prompts appear only where required. | NOT TESTED |
| Existing-install upgrade | Normal installer previews/reconciles the update; existing Android state, saves, shell preferences and configured apps survive. | NOT TESTED |
| Same-version repeat | Verified work is skipped; incomplete work remains actionable. No duplicate managed shortcuts or repeated completed installer launch. | NOT TESTED |
| Setup report | `deckctl setup report` agrees with actual state and supplies targeted retries. Exit 2 for unfinished setup is not a crash. | NOT TESTED |
| Android | Android opens, existing user state survives, and Google Play opens/signs in as appropriate. `deckctl android status` reports READY only with required state present. Do not reinitialize a working image. | NOT TESTED |
| Decky | Loader opens and selected plugins actually load. Record unavailable/incompatible plugins rather than marking them installed. | NOT TESTED |
| CSS | Real selected Theme Store components load; supported palette settings take effect. Record unavailable controls/components explicitly. No fake Bubble Gum Rave theme. | NOT TESTED |
| Shortcuts/art | Desktop shortcuts have usable icons and launch their targets. Gaming Mode artwork remains managed by SteamGridDB. | NOT TESTED |
| Installer cleanup | Completed staged installers no longer mislead users into reinstalling; installed EmuDeck manager remains usable; failed/incomplete setup remains retryable. | NOT TESTED |
| Terminal/controller | Prompt and tmux open; controller tooling and the selected profile work in an actual game/app. Existing preferences survive repeat setup. | NOT TESTED |
| Media/launchers | Selected media shortcut and game launcher open; logins remain explicit user actions. | NOT TESTED |
| Remote/network | Moonlight connects to a configured Sunshine host; Tailscale status matches the actual connection. Never attach keys or pairing credentials. | NOT TESTED |
| Recovery | Complete relevant safe tests below and document omissions. | NOT TESTED |

## Recovery tests

Read each command's `--help` before a state-changing test. Record the starting
state and recovery location. Do not simulate power loss, remove a mounted card,
or interrupt a system/vendor package operation.

1. **CSS/UI:** capture with `deckctl decky css capture`; exercise `deckctl ui safe`
   and `deckctl ui restore`; confirm the previous visible profile returns.
2. **Interrupted download/retry:** interrupt only an isolated test download;
   restore networking and use the retry reported by `deckctl setup report`.
   Confirm incomplete output is not reported READY and successful retry converges.
3. **Backup/restore:** use a backup with disposable test data; inspect
   `deckctl restore ARCHIVE --dry-run` before restoring selected categories.
   Confirm contents, retained unrelated files and rollback copies.
4. **Self-update/rollback:** on a test installation, follow
   `deckctl update --help` and the [operations guide](OPERATIONS.md). Verify the
   selected version and preserved user state after update and rollback.
5. **Storage migration:** when a DECK-EMU test card is available, use the supported
   migration workflow and `deckctl storage verify-migration`. Finalize only after
   verification; check emulator launch and save/load. Retain the rollback copy.
6. **Post-SteamOS-update:** test after an actual supported OS update when available;
   use `deckctl post-update --help`. Otherwise mark this scenario NOT TESTED.
7. **Support bundle:** generate with `deckctl support-bundle`, inspect locally,
   and confirm it excludes credentials, cookies, private keys, ROMs, BIOS, saves
   and personal backup payloads. Do not upload a bundle automatically.

## Release decision

Link failures to issues and record whether they block release. Compare expected
configuration with actual results; a status string alone is insufficient. Add
only evidenced combinations to the [compatibility record](COMPATIBILITY.md).
Record vendor outages separately from project failures without concealing either.
