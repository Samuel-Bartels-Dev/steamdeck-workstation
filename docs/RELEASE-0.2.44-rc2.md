# Steam Deck Workstation 0.2.44-rc2

This clean candidate contains all changes merged through PRs #58 and #60,
including the earlier 0.2.44-rc1 fixes. Install from the versioned tarball or USB
ZIP and verify its SHA-256 manifest. Existing selections, completed components,
Android images/apps/login state and upstream recovery files are preserved.

- Setup uses the existing KDE password dialog for the first administrator
  operation and shares sudo's temporary authorization across Install, Retry,
  Resume, Desktop CSS bridge work and supported provider subprocesses while the
  owning app stays open. Close/crash cleanup ends authorization and terminates
  owned operations. No passwords are saved or persistent bypass rules added.
- Android runs inside the shared queue and console. Its genuine image chooser
  and sign-in windows remain visible; completion requires image and user state,
  not just a successful launcher exit. Nested Desktop defers provider work that
  could restart Decky and disrupt the hosting Steam session.
- The reviewed upstream adapter retains compatibility, fingerprint/bundle,
  storage and protected repair checks. Launcher display detection drains output
  to avoid SIGPIPE/status 141 while preserving real failures. Steam shortcuts
  use a pinned persistent runtime, with exact known wrapper migration and
  preserved vendor bytes. Unknown provider/custom launcher changes fail clearly.
- CSS uses the exact approved Store and native name, Game Cover Shine Animation
  Color, while keeping existing saved IDs. Profiles remain incomplete when a
  selected component fails. Normal Desktop works without switching sessions.
- README documents fixed-version installation and `deckctl setup cleanup`.
  Cleanup removes only verified, unchanged staged installers. Unverified EmuDeck
  setup, Android recovery files and installed data remain available.

Validation before packaging: 448 repository tests across 17 modules, repository
lint, Android lifecycle/preservation regressions, and GitHub CI on the merged
implementation passed. Tests use fake sudo and process fixtures; live display,
provider contract and Store inspections were read-only. Release delivery verifies
both independently extracted archives, modes and checksums, then exercises the
published bootstrap without provisioning the runner.

The user reports that installations tried so far are working. This is partial
hardware feedback, not a completed fresh-install, interruption, reboot, Desktop
and Gaming Mode acceptance matrix. Candidate status remains until those gates
have reviewed evidence. Android boot/sign-in, controller health and real
close/reopen authorization behavior still require explicit hardware checks.

After installing, run `deckctl setup cleanup --dry-run` and then
`deckctl setup cleanup`. Preserve an Android-pinned runtime until Retry from the
new installed runtime migrates its exact generated wrapper. Do not reinstall or
reset Android merely to update the installer.
