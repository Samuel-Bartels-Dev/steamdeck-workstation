# Installer and maintenance script reference

All user-facing entry points below accept `--help` without installing software.
For the complete command tree, see [COMMANDS.md](COMMANDS.md). The normal user
entry point remains `./install.sh` in Desktop Mode, without sudo.

| Entry point | Invocation | Behavior and expected result |
|---|---|---|
| Normal installer | `./install.sh` | Validates the release, copies the control plane into persistent user storage, applies enabled modules, then offers guided vendor/account setup. Repeated runs use existing readiness checks. Module failure produces a nonzero final exit code; guided setup remains available. |
| Internet installer | `./bootstrap.sh` | Downloads and verifies the published GitHub release, then runs the normal installer. Use `--download-only DIRECTORY` to save it without installation. |
| Uninstall guidance | `./uninstall.sh` | Prints vendor-removal guidance. No destructive bulk uninstall or save deletion. |
| Persistent command install | `tools/install-control-plane [SOURCE]` | Copies a trusted repository into the versioned releases directory, installs aliases and the man page, and atomically promotes the current link. Reusing a version with different bytes/modes is refused. It does not install vendor applications. |
| Build release | `tools/build-release [OUTPUT]` | Runs the full regression gate, then builds the repository tar, USB ZIP, and checksum manifest. Default output is `release/`. Same-version output artifacts are replaced after building the complete new set. `tools/package-release.py` is the underlying equivalent. |
| Verify packages | `tools/verify-release.py OUTPUT` | Checks final checksums and USB layout, extracts both repository copies independently, compares every source file and mode, and runs regression tests in each. Exits nonzero on any failed gate. |
| Repository validation | `tools/validate-modules` | Equivalent gate to `deckctl repo validate`, including module contracts, syntax, baseline preservation, help, and behavioral tests. |
| Documentation validation | `tools/lint-docs` | Checks local inline Markdown file references. External URLs and heading anchors are outside its scope. `tools/check-docs.py` is the equivalent implementation. |
| Generate manuals | `tools/render-command-docs.py [--check]` | Generates `docs/COMMANDS.md` and `docs/man/deckctl.1` from runtime command metadata. `--check` compares without writing and fails on drift. |
| Support-bundle guidance | `tools/redact-support-bundle` | Advisory only. It does not redact arbitrary archives. Use `deckctl support-bundle` to create a fresh allowlisted diagnostic bundle. |
| AI instruction guidance | `tools/sync-ai-instructions` | Advisory only. Shared instructions live in `docs/ai/COMMON.md`; no generation occurs. |

## USB installer

The ZIP's `INSTALL.sh [--help]` verifies the nested tar against `SHA256SUMS`,
extracts it to a temporary directory with Unix permissions, and runs the normal
installer. It refuses root. Temporary extraction is removed on exit; the
persistent installed release remains available after USB removal. Internet is
required for vendor payloads and authentication.

## Installed aliases and shell helpers

`deckctl aliases` lists every project alias and its expansion. For an alias that
expands to a deckctl command, append `--help` or use `deckctl help` with that
expanded command path. Aliases have the same effects and exit status as their
underlying commands. See [terminal module](../modules/terminal/README.md) for
terminal-only aliases and upstream tools (use those tools' own `--help`).

The tmux helpers retain their existing interface:

| Helper | Meaning |
|---|---|
| `tm` | Create or attach the persistent main session. |
| `tml` | List tmux sessions. |
| `tma [name]` | Attach/switch to a session. |
| `tmk [name]` | Kill a session after confirmation; its running processes end. |
| `tmhelp` | Show the configured tmux key cheat sheet. |

## Module and host scripts

`modules/*/install.sh`, `verify.sh`, and `doctor.sh` are internal module actions,
not standalone CLI entry points. Run them through deckctl so dependency order,
`DECKCTL_ROOT`, `DECKCTL_CONFIG`, and `DECKCTL_STATE` are established. Their module
README and manifest describe prerequisites and behavior. Do not pass generic
options directly to vendor scripts: their interfaces belong to the vendor.

The Windows host kit is explicitly exported using `deckctl remote host-kit`.
Its PowerShell scripts run on the Windows host, never in the Deck provisioning
graph; see [host instructions](../host/windows/README.md).

## Exit status and privacy

Help exits 0; invalid argparse usage exits 2. Operational failures are nonzero.
`deckctl verify` and `doctor` return 1 for failed/absent modules, 2 for
configuration-required/degraded state, and 0 for ready/optional modules.
Diagnostic commands such as `health` print per-item states; successful report
generation is not proof that all reported components are ready.

Private backups and inventory exports are different from sanitized support
bundles. Never publish personal backups, host kits, or inventories without
reviewing their contents. Portable profiles allow approved JSON, controller
VDFs, and recognized CSS profile image formats; arbitrary scripts/folders,
symlinks, and invalid JSON are excluded or rejected.
