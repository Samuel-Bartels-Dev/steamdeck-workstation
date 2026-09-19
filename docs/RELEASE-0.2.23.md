# v0.2.23 — preflight on existing installations

The v0.2.22 regression preflight simulated an absent Decky Loader by changing
HOME, but still queried the real system-wide plugin_loader.service. A previously
provisioned Deck with Decky enabled therefore failed the orphan-plugin assertions
before software installation began. This was a test isolation bug, not evidence
that the user's Decky installation was broken.

The orphan-state presentation test now explicitly supplies an absent Loader.
The real detector remains unchanged and is separately tested against enabled,
disabled, failed-service and installed-executable states. Regression subprocesses
use temporary HOME, deckctl configuration/state, and XDG locations.

The normal installer supports both fresh and existing installations. It installs
a versioned control-plane copy, promotes the current symlink, and retains the
previous release. Existing modules perform their normal idempotent convergence;
completed guided steps are detected and skipped. No wipe or Decky removal is
needed. Account sign-in remains interactive when required by vendors.

Use the new release's normal installer (USB: `bash INSTALL.sh`; extracted repo:
`bash install.sh`). The v0.2.22 failure happened before provisioning, so there is
no partial application migration to undo from that failed run.

Upgrade tests seed an earlier installed release, Android image/user state,
CSS configuration, plugin selections, Steam shortcuts/artwork, recovery profiles,
and shell customizations. They install the new control plane twice and verify
that these payloads and the previous release remain intact. Simulated vendor
state does not replace physical Steam Deck acceptance testing.

All v0.2.22 CSS/Waydroid features are retained. Live Theme Store download and visual
compatibility limitations from v0.2.22 remain; this maintenance release does not
claim new live Store or hardware validation.

## Verified installer cleanup

After provisioning and each guided step, known unchanged EmuDeck, Decky, Android
and completed Tailscale installer shortcuts are removed when their installation
is verified. EmuDeck staging is skipped once the installed manager and vendor
completion markers exist. Exact legacy EmuDeck downloader copies are recognized.
Other edited/untracked files and application shortcuts are preserved.

Use `deckctl setup cleanup --dry-run` for a preview or `deckctl setup cleanup`
for cleanup on an already configured Deck. Status commands remain read-only.
No broad Downloads or ZIP deletion is performed. Temporary vendor archives retain
their existing cleanup handlers. Automatic self-update deletes its own unchanged
downloaded tarball only after validating and promoting the release. Explicitly
supplied release archives, USB bundles, prior releases and rollback data remain.
