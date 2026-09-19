# Engineering review — v0.2.20

This review uses the delivered v0.2.19 tree as its immutable starting point.
It retains all 16 modules and their existing domain boundaries. The v0.2.18
Waydroid implementation remains byte-for-byte protected. v0.2.19's CSS Loader
Theme Store integration, configurable Bubble Gum Rave palette, Decky selection,
and Desktop icon/SteamGridDB separation remain in place.

## Scope and disposition

Reviewed the CLI, shared Python libraries, module manifests and actions,
installer, recovery/update operations, terminal tooling, controller/storage
operations, remote host kit, documentation, contract tests, and packaging.
The goal was concrete reliability and interface improvements without replacing
working subsystems or adding a new framework.

| Finding | Implemented change | Evidence |
|---|---|---|
| Most command help lacked operational detail | Explicit descriptions, effects, examples, file locations, options, and exit statuses for every registered command; group summaries and `deckctl help PATH`; `--version`; offline Markdown and man page | Tests enumerate every parser and execute both help forms in an empty HOME; generation drift check |
| Help and status could write state | Removed eager config/state mkdir at import and controller status/verify writes; setup status no longer creates a shortcut; apply explicitly creates the resume shortcut | Empty-HOME tests and module verification test |
| Failures could appear successful | Apply aggregates failed modules while continuing; installer retains guided flow and final failure status; verify and doctor aggregate readiness; post-update records component failures | Exit-code/state tests; existing setup regressions |
| Verifier contract too permissive | Validated readiness enum; bounded verifier subprocess; no READY on nonzero exit; workspace verifier emits structured readiness | Invalid/failed/timeout verifier tests |
| Profile export recursively copied unknown folders | Explicit portable-file allowlist, JSON parsing/redaction, image signatures, no symlinks, bounded files; invalid JSON is never copied verbatim | Private payload exclusion and roundtrip test |
| Profile import accepted executable/untrusted paths | Complete file preflight, approved formats, link checks, private atomic writes, rollback copies and rollback on write failure | Unsupported payload and destination-link tests |
| Release/profile extraction accepted excessive or unusual payloads | Bounded counts and expanded bytes; reject duplicate paths, backslashes, traversal and special entries | Malicious ZIP/tar fixtures |
| Rollback could interpret an empty history path as cwd | Require a real previous release within the managed release directory; validate required files | Empty/outside-history test |
| Persistent installation deleted an existing release before replacement | Validate version/aliases first, lock installation, stage a complete copy, refuse differing same-version content, atomically replace links after preparation | Repeat install, conflicting-content preservation, installed man page test |
| Shared JSON writes used one predictable temp name | Unique private temp file, flush/fsync, atomic replace | Resulting JSON, permissions, and cleanup assertions |
| SSH relay command lost Python argument quoting | Send one shell-quoted remote command; reject option-like relay values and invalid ports | Decode/compile actual remote argv test |
| Host-kit name could escape its directory | Safe filename validation, require registration, unique temporary build directory | Traversal/unknown-host rejection test |
| Terminal update deleted a working binary when verification failed | Verify staged replacement before atomic promotion; bound verification time; constrain receipt-driven deletion to managed locations | Failed candidate leaves known-good bytes unchanged |
| Tailscale refresh removed the previous setup tree before downloading | Stage and validate the new checkout/archive first; preserve previous content as a backup | Simulated clone failure retains original file and cleans stage |
| Storage finalization could rename a live migration symlink | Treat existing redirection as already finalized; unique rollback names | Existing link preserved test |
| Backup restore trusted arbitrary category/source metadata | Validate format/category, reject special/traversal entries, constrain WoW locations, reject destination links, retain prior files in state/restore-rollback | Invalid category/version tests plus existing recovery guards |
| Desktop Exec quoting used shell quoting directly | Shared Desktop Entry argv encoder for setup/workspace launchers | Escaping-layer roundtrip test; existing icon/shortcut tests |
| Documentation tool only listed files | Actual local inline Markdown file-reference check | Repository gate |
| Baseline protection needed to remain explicit | Preserve original v0.2.18 manifest; add v0.2.19 file snapshot and explicit reviewed-file inventory | Every original file exists; unchanged files match exact hashes; Waydroid unchanged |

## Interface decisions

`deckctl` remains the supported control plane. Detailed help metadata is separate
from dispatch, but the parser is still the command registration authority. Tests
fail when a new command or argument lacks documentation. Both manual formats
are generated from that parser, avoiding a second hand-maintained command list.
Unknown long-option abbreviations are rejected to prevent future options from
changing existing command interpretation.

Status inspection is distinct from reconciliation. Apply, doctor, and post-update
may mutate managed state; help and verifiers do not provision or repair. Readiness
states remain visible when authentication or platform interaction is required.
No global TDP/display changes, package-manager changes, or Waydroid redesign
were introduced.

Portable profiles are intentionally data-only. Shell/tmux executable configuration
is regenerated by `terminal apply --config-only`; arbitrary config folders do not
travel through profile export. Supported CSS profile settings/images and controller
VDFs remain portable. Personal backup/restore is a separate trusted-backup
interface and may contain private application state. Support bundles retain their
narrow sanitized allowlist.

## Remaining boundaries and follow-up

- Real Steam Deck hardware, Steam client UI, Flatpak installations, Windows host
  execution, authentication, streaming, and vendor installers were not executed
  in this build environment. Offline fixtures verify resulting state and failure
  handling, not end-to-end hardware compatibility.
- Live Decky/Theme Store requests were blocked in the preceding release build
  environment. Native CSS Loader/store behavior remains covered by schema and
  backend fixtures; a successful live store installation is not claimed here.
- Existing vendor installers download upstream code. Checksum comparison detects
  corruption but is not a signature or independent trust proof. Version pinning
  and signature policy across all vendors require a separate compatibility and
  update-policy change, especially for protected Waydroid.
- CSS capture/restore preserves exact user profile contents locally. Only the
  portable exporter applies its strict format allowlist; custom unsupported asset
  types are excluded from portable bundles with guidance.
- Backup restore keeps prior files but is not a cross-filesystem atomic transaction.
  Interrupted restores may need the retained rollback copy. Backups are private
  trusted input, not executable bundles from strangers.
- Existing remote/network health reports can complete with warnings; inspect their
  item states. Use `verify` for aggregate module readiness in automation.
- Full source formatting/type-annotation modernization was deferred to avoid
  obscuring behavior changes with a broad rewrite. Existing dense code remains
  a maintainability follow-up; no claim of an exhaustive security audit is made.

## Reference standards

Implementation decisions follow the official [argparse documentation](https://docs.python.org/3/library/argparse.html),
[tarfile extraction guidance](https://docs.python.org/3/library/tarfile.html#extraction-filters),
and [Desktop Entry Exec specification](https://specifications.freedesktop.org/desktop-entry/latest/exec-variables.html).
These complement the project's existing [engineering principles](PRINCIPLES.md).

## Validation result

The repository gate passed: existing regression contracts, 28 v0.2.19 behavioral
tests, and 30 v0.2.20 review tests. Help checks cover all 124 parser pages via both
`--help` and `deckctl help PATH`. Syntax, executable modes, module registration,
manual generation, local documentation targets, and baseline inventories pass.
Package verification reruns this same gate in both independently extracted copies.
