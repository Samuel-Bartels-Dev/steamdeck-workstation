# Production readiness review

Audit started 2026-09-24 against the v0.2.43 working tree. This is source inspection,
not a fresh-install or hardware certification. Existing unrelated AGENTS and
baseline-inventory edits are retained. No vendor installer is run during this review.

## Findings before implementation

| Area and source inspected | Existing behavior | Gap / regression risk |
| --- | --- | --- |
| `bootstrap.sh`, `install.sh`, `tools/install-control-plane` | Public stable resolution, exact asset identity, SHA-256, bounded safe extraction, durable command, rollback history | Bootstrap accepts stable versions only; installer runs the entire development regression suite twice on re-exec. No common run history or machine preflight before control-plane promotion. |
| `lib/deckctl/core.py`, module manifests/actions, `module.sh` | 17 modules, dependency ordering, real verifiers, nonzero verifier cannot claim READY; atomic private JSON writes | `doctor` invokes mutating scripts while CLI overview calls it diagnosis. Per-module timeouts do not bound entire health duration. |
| `setup_plan.py`, `setup_install.py`, `setup_window.py` | Individual selections, dependency closure, saved plan fingerprint, flock, resume re-verifies, failed dependencies blocked, GUI reports remaining work | Allowances cover only some payloads. Installed updates can bypass the per-item space check. Run state overwrites previous attempts; no correlated historical plan/results. |
| `install_log.py`, `install_progress.py` | Private bounded redacted stderr logs, live phases and byte progress | Same item overwrites prior log; stdout is not captured; terminal still gets raw stderr. Arbitrary provider output cannot be guaranteed secret-free. Interactive vendor prompts require a visible terminal. |
| `lifecycle.health`, CLI health dispatch | Read-only module/storage/setup summary | Always exit 0, even on failures. Unbounded in-process DNS lookup. No distinction between module readiness and compatibility certification. |
| `core.storage_health`, `storage_ops.py`, storage module | lsblk labels/UUIDs; guarded EmuDeck migration; preserves original content | Inventory is not destination validation. Missing role cards disappear from output; no common writable/read-only/UUID expectation preflight. No offline filesystem-health proof. |
| `decky_installer.py`, Decky module | Real loader independent of plugin folders; Store-only source, ZIP identity/traversal checks, staging/backup, audit | Installed package is not proof plugin loads. Local archive hash is a receipt, not upstream checksum verification. No OS/Decky compatibility resolver; latest catalog selection not a tested pin. |
| `css_stack.py` | Real backend/schema controls; exact Store identity; saved/live verification; reversible safe mode; captured profiles | Actual visible Game Mode result still needs hardware. Do not replace this with marker-based success. |
| `android.py`, Android module | Protected existing-image repair; user-state distinction; bundled launcher and explicit reinstall | Image + user directory is not Android boot/Play/controller health. Provider branch changes independently. No kernel/SteamOS evidence gate. |
| gaming/emulation/remote modules, `launchers.py` | Heroic/Moonlight Flatpaks; EmuDeck owns migration; Tailscale-specific installer; Sunshine companion isolated | Pairing, playback, vendor installer completion need human validation. Some raw upstream installer downloads lack independently published digest verification. |
| `containers.py` | Rootless Docker prerequisites, pinned checksummed assets, Compose smoke, scoped cleanup, user service and context awareness | Generic rootful docker.service assumptions would break this project. Presence/API/smoke are deliberately distinct. Container smoke changes state and must not be a default SAFE test. |
| media/workspace, `desktop.py`, `controller.py` | Selected web apps, duplicate guards, managed artwork, preserved symlinks, captured templates | Steam reload and account auth remain manual. Directory/file presence alone cannot certify playback or controller behavior. |
| `terminal.py`, `appearance.py`, developer/AI tools | User-space payloads, receipt hashes, version comparison, preserve unmanaged tools, temporary staging; Ollama owned on-demand process | Some writes are non-atomic; checksum enforcement varies by provider. Model manifest/blob checks are not inference tests. Retained runtime trees cannot be blindly deleted. |
| `reliability.py`, `setup_cleanup.py`, `upgrade_plan.py` | Portable allowlist; preflight/rollback on profile import; sanitized explicit support inventory; only hash-matched installer cleanup; release rollback | No correlated logs in bundles; no blanket safe cache deletion; rollback does not undo vendor changes. Redaction must not imply all arbitrary logs are safe to share. |
| tests/contracts and integration, `tools/lint-repo.py` | Extensive dirty-state/failure/archive/profile/CSS/shortcut regression coverage, Py 3.12/3.13; real Compose and Qt jobs; Ruff/ShellCheck/actionlint/docs checks | No unified SAFE harness or performance history. PowerShell companion exists without dual-runtime syntax gate. Markdown lint/shfmt are not current gates. |
| `.github/workflows`, packaging, compatibility docs | Pinned Actions, CodeQL/dependency audit, secret-pattern scan, independent extracted package tests | VERSION push publishes directly stable. No required hardware evidence/RC promotion gate or public released-path smoke. Compatibility record is prose, not runtime policy. |

## Documentation discrepancies

* CLI overview says diagnose; actual `doctor` can install, rewrite configuration,
  launch applications, and even create a backup. Shared principles also describe
  doctor as repair. The new public interface must separate these explicitly.
* `docs/TESTING.md` describes several already-required checks as optional.
* Storage discovery reports READY when lsblk exists; that is not card health.
* Decky post-install audit is a filesystem audit, not a plugin-load certification.
* A successful `health` process currently cannot serve as a release gate.

## Implementation order and exact intended ownership

1. Observability: add `lib/deckctl/run_log.py`; integrate `setup_install.py` and
   existing `install_log.py`, expose CLI logs. Preserve interactive provider I/O;
   migrate unattended operations incrementally, never hide password prompts.
2. Safety: add `lib/deckctl/preflight.py`, `compatibility.py`, and a reviewed JSON
   compatibility record. Reuse existing selection/storage allowances. Unknown
   sizes/compatibility remain warnings, not manufactured support or capacity.
3. Reliability: fix health exit contract; make public doctor read-only and expose
   explicit repair. Keep existing module-specific repair implementations.
4. Tests: add focused production contracts and safe command harness; run existing
   regression and packaging gates. No real installation or destructive injection.
5. Release: enforce reviewed evidence before stable publication; add public
   bootstrap smoke and RC support; document remaining physical gates and results.

## Architectural constraints

The code is deliberately Python standard library plus shell, not a service.
Different provider installers need interactive terminals; one universal output
capture would break them. There are two installation paths (module apply and
per-item setup) plus direct specialist commands; incremental observability must
state exactly which paths are covered. Existing regression inventories record
reviewed changes; preserve historical hashes rather than regenerating baselines.
Compatibility information must not infer tested status from a matching major
version. Hardware results apply only to their exact version/model/component scope.

## Initial release recommendation

Not yet certified for production by the requested gates. Preserve known-good
behavior; automate the missing gates and collect T01–T06 evidence before stable
promotion. No current source review can certify a fresh Deck, reboot, Game Mode,
new SteamOS build, vendor authentication, or actual plugin loading.

## Implemented engineering pass

The implementation preserves the existing module architecture and immutable-root
policy. New shared files are `run_log.py`, `preflight.py`, `compatibility.py`,
`diagnostics.py`, `downloads.py`, `production_cli.py`, and `safe_tests.py` under
`lib/deckctl`. The exact Git diff is the authoritative changed-file inventory.

* Unique private run journals, structured events, saved plans, durations, bounded
  per-item log copies, retention with live-run/newest-failure protection and CLI
  log commands. Setup, apply, update-apply, repair and SAFE tests are covered at
  their CLI orchestration boundary. Unattended Flatpak output is captured with
  a failure tail; interactive provider prompts are preserved.
* Read-only preflight and compatibility commands. Known storage allowances are
  grouped by filesystem with configurable reserve; separate temporary storage
  receives a conservative allowance. Unknown sizes warn. Per-item upgrades no
  longer skip their staging-space checks.
* Actual mount and expected UUID/filesystem/target checks, duplicate-label and
  read-only rejection; absent optional cards remain distinct from failed cards.
* Health no longer returns success for failed modules/storage. Its implicit
  unbounded DNS lookup was removed. Public doctor is read-only; explicit targeted
  repair delegates to established providers. No rootful Docker assumptions.
* Compatibility has a reviewed JSON schema and exact-system evidence matching.
  No complete certification was invented. Unsupported selected plugin versions
  are blocked before artifact download; unknown Store selections warn.
* Atomic bounded staged desktop-installer downloads reject HTML, truncation and
  checksum mismatch when an expected checksum is provided. The first migration
  is NonSteamLaunchers in the per-item path. Other vendor downloaders are retained.
* Managed appearance writes now atomically replace only completed temporary files.
* Support bundles add compatibility and allowlisted run summaries, excluding raw
  provider logs. Existing credential/configuration allowlists are preserved.
* SAFE quick/full/module diagnostics, isolated harness entry points and 19 new
  production contracts. Full does not silently run state-changing container tests.
* Release archives now stage on the output filesystem: actual build testing
  exposed and fixed EXDEV when /tmp and the destination are different devices.
  A failure-injection regression protects this case.
* RC syntax accepted by bootstrap, packaging and control-plane installation;
  default bootstrap remains stable. Stable publishing requires reviewed exact-
  source evidence. Public bootstrap smoke runs after publication and independently.
  Windows PowerShell 5.1/7 syntax jobs do not execute host provisioning.

## Verification evidence and boundaries

The existing full repository suite passed across all 17 modules during this pass.
The focused production suite passes 19 tests, including independent candidate
control-plane install in a temporary home, explicit-public-RC resolution,
retention, interruption, symlink protection, read-only doctor, failed health exit,
future OS rejection, wrong/ambiguous cards, atomic-write failure, partial download,
HTML/checksum failure and stale/unpassed stable evidence. Existing setup appearance
contracts also passed. Static checks cover 74 Python files, 69 shell files and
five workflows. Logs are retained locally under `~/.cache/deckctl-review/` with
`production-` filenames; these are engineering evidence, not public hardware logs.

Read-only local checks identified OLED, SteamOS 3.8.16 build 20260716.1. Offline
preflight and storage exited 2 (warnings); this is not a production PASS. GitHub quality, security and packaging workflows passed for the initial implementation, including Windows syntax checks. The new public-release smoke cannot run before publication. A live Flathub probe failed DNS resolution even outside the sandbox; connectivity remains unverified here. No release
has been published or promoted by this work. Packaging/extracted validation is a
separate final check reported in the handoff; local tests are not physical T01–T06.

## Remaining gaps, deliberately not claimed complete

| Area | Remaining work / risk |
| --- | --- |
| Output/logging | Not every direct vendor/module entry point is migrated. Interactive stdout is still terminal-owned. No universal quiet/debug flags or 250 MB total quota. Abrupt kill can leave RUNNING history. |
| Compatibility | No complete certified matrix; Decky version discovery and authoritative provider constraint adapters remain unresolved. Unknown plugin selection currently warns, rather than a separate risk-policy chooser. No remote refresh or automatic version fallback. |
| Capacity/downloads | Vendor peak sizes/shared runtimes are partly unknown; Flatpak/vendor checks still matter. No complete bandwidth/retry metrics for all downloaders. Not all downloads have upstream digests, and local receipt hashes are not publisher verification. |
| Preflight | Not yet universal for bootstrap/control-plane/direct specialist commands. Dependency executable presence is not version compatibility. No offline fsck/SMART claim or complete upstream endpoint inventory. |
| Repair/verification | Legacy repair implementations retained; some are broad within a targeted module. Plugin package audit is not actual load; Android state is not successful boot/Play; controller presence is not in-game function. |
| Tests | Full network/fs-full/sudo/extraction/power-cut matrix and Minimal/Gaming/Development/Full machine profiles are not all automated. No noisy timing CI failure threshold. Human upgrade/reset/SteamOS tests remain mandatory. |
| Release gates | Evidence validation is structural/source-bound, not proof of human assertions. Branch protection and required-check settings need repository-owner configuration. New Windows/public-smoke jobs must run in GitHub. A post-publish failure cannot undo publication. |
| Configuration/cleanup | Atomic appearance writes improved, but not every managed config has bounded backups. Cleanup does not delete unknown staging/runtime trees or user content. Component rollback is not universally supported. |

**Recommendation:** ready for engineering review and candidate testing, not stable
certification. Follow [the physical commands and pass/fail checklist](PRODUCTION-OPERATIONS.md).
A new candidate version is required before installing this changed tree over the
existing v0.2.43 control plane. Preserve the previous stable release for recovery.

Final local clean-source package verification passed: 373 files, two independent extractions, matching nested archive, executable modes, SHA-256 and both extracted regression runs. A subsequent narrow network-probe change uses the existing real Flathub repository endpoint with HTTPS-only redirects; focused contracts and static checks cover it, with GitHub validation rerun on the updated head.
