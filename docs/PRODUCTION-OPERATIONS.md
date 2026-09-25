# Production diagnostics and release validation

This engineering pass adds foundations; it does **not** certify this release on
fresh hardware. See [the inspection and gap analysis](PRODUCTION-READINESS-REVIEW.md)
and [existing hardware checklist](HARDWARE-TESTING.md).

## Commands and state

Run from the candidate checkout while testing, so you test this implementation:

```bash
./bin/deckctl preflight --json
./bin/deckctl preflight --online
./bin/deckctl compatibility --verbose
./bin/deckctl storage --json
./bin/deckctl health --json
./bin/deckctl doctor docker --json
./bin/deckctl doctor decky --json
./bin/deckctl doctor waydroid --json
./bin/deckctl test quick --json
./bin/deckctl logs latest
./bin/deckctl logs errors
./bin/deckctl cleanup --dry-run
./bin/deckctl support-bundle
```

Capture stdout/stderr and each exit code immediately with `echo $?`. Exit 0 is a
pass, 1 is failure, and 2 means warning/configuration required. In particular,
compatibility UNKNOWN returns 2; it is **not** a supported result. Optional absent
SD cards warn, while configured required cards fail. Health uses existing module
verifiers, so authentication/first-run configuration can return 2 even when the
software is installed. Docker API availability is distinct from a container test.

`doctor` now diagnoses without repair. Use `repair MODULE` deliberately for the
existing module repair action; `repair docker` uses the rootless container
provider, `repair waydroid` uses protected Android repair, and `repair shortcuts`
previews existing shortcut repair. There is no implicit repair-all. Legacy
module `doctor.sh` files remain internal repair implementations.

`test quick` and `test full` are SAFE: they run verifiers, record timings and
write only their own diagnostic journal. Full adds bounded network probes; it
does not boot Android, launch containers, or install anything. `test module decky`
runs a single verifier. `tests/run-tests.sh --unit` runs isolated production
contracts, `--regression` runs all repository contracts, and `--integration`
runs the isolated Qt UI test. The existing live container integration is
MODIFIES_STATE and remains an explicit separate command. Destructive reset,
forced-full-disk, card removal during writes and power-cut tests are not automated.

## Logs

The established project state root remains `~/.local/state/deckctl`, overridable
with `DECKCTL_STATE`. Each CLI setup-install/apply/update-apply, explicit repair,
and SAFE test has a unique private directory under `logs/` with:

* `result.json`: operation, version, exit status, run ID and duration.
* `events.jsonl` and `run.log`: correlated events.
* `plan.json`: installation/preflight plan or SAFE test result where applicable.
* Hashed item `.log` files: bounded copies of installer stderr for setup items.

`logs list`, `logs latest`, `logs errors`, `logs show terminal:ghostty` are
read-only. `logs clean` keeps 10 install/apply/test runs, 5 repair/update runs,
failures for 30 days, and the newest failure indefinitely. `logs clean --all`
still preserves live runs, newest failure and unrecognized content. A killed
process can leave RUNNING history; setup's lock-based snapshot independently
identifies interrupted items. Journals have per-file limits; this is not yet a
250 MB global quota.

Unattended Flatpak output goes to item logs with a failure tail. Use
`setup install --verbose` to also see it live. Interactive vendor I/O remains in
Konsole. Direct specialist commands are not all migrated to the run logger yet.
Support bundles include **allowlisted run summaries**, not arbitrary raw logs:
redaction is defense in depth and cannot certify all third-party output safe.
Review any bundle before sharing it. Credentials and browser stores are excluded.

## Preflight, capacity and compatibility limits

Preflight runs before CLI `apply` and `setup install` provider operations. It is
not yet a universal gate for bootstrap's small archive, control-plane copying,
or every directly invoked vendor command. Architecture, required command
presence, OS/model, write access/mount flags, existing conservative staging
allowances, reserve and HTTPS connectivity are checked. Sudo availability does
not prove authorization. Version compatibility of all dependencies is not yet
known. The network probe covers GitHub/API/Flathub, not every vendor/CDN path.

The existing 1 GiB minimum reserve is retained as a floor; configure a larger
integer `storage_reserve_bytes` in settings.json. This is not a claim that 1 GiB
is sufficient for all SteamOS updates. Known allowances are summed by filesystem;
unknown vendor sizes and shared Flatpak runtimes are explicitly excluded and
warn. Per-item checks run again, including updates. Free space can change after
preflight; no estimate guarantees completion. Storage identity checks do not run
fsck, SMART or destructive write tests.

Optional `settings.json` storage expectations use this form:

```json
{"storage_devices":{"emulation":{"label":"DECK-EMU","uuid":"YOUR-UUID","filesystem":"ext4","mount":"/run/media/deck/DECK-EMU","required":true}}}
```

Only configure actual values from your card. `pc_games` is the other role.
Duplicate labels, mismatched expected UUID/filesystem/mount, stale mount paths
and read-only destinations fail. An absent optional card remains a warning.

`compatibility/records.json` is a reviewed, versioned local evidence database.
It starts with no full certifications, intentionally. Records identify component,
component_version, os, version, build, architecture, model, kernel, decky_version,
date, evidence and TESTED/SUPPORTED/UNSUPPORTED status. Exact identity is required;
plugin support additionally needs a known matching Decky version. Current runtime
Decky-version discovery is unresolved and reports unknown; do not populate fake
values to make it green. Installed plugin versions come from package.json.
No arbitrary remote compatibility refresh is trusted. Selected Store downloads
warn on UNKNOWN and block matching UNSUPPORTED records. Package checks still do
not prove successful plugin loading.

## Release candidates and stable gates

Use a new VERSION such as `0.2.44-rc1` and matching release notes; update the
release-version assertions normally. Packaging, control-plane install and explicit
bootstrap versions accept `-rcN`. Default bootstrap still selects stable only.
Candidates publish as GitHub prereleases. Do not publish this working tree under
the already-used 0.2.43 version: same-version different content remains refused.

Stable publication now requires manual workflow input `evidence` naming a
reviewed JSON report in the checkout. A VERSION-only stable push intentionally
fails closed. Obtain the implementation fingerprint with:

```bash
python3 tools/release-gate.py --fingerprint
python3 tools/release-gate.py --report docs/validation/YOUR-REPORT.json
```

The report requires schema_version 1, version, candidate (`VERSION-rcN`),
source_sha256, date, tester, hardware, steamos, kernel, decky and `gates`. Each gate
must be an object containing `status: "PASS"` and nonempty `evidence` pointing to
reviewable results. Required gates are ci, unit, integration, compatibility,
storage, fresh_install, idempotency, upgrade, interrupted_install,
dirty_state_repair, health, reboot, desktop_mode, gaming_mode, support_bundle and
public_bootstrap. Skips and unknowns block stable. Keep incomplete reports with
NOT_TESTED states while collecting results. The checker validates report shape
and exact implementation fingerprint; reviewers remain responsible for the
truth of human evidence. It cannot remotely perform physical tests.

The fingerprint covers implementation/configuration/tests/workflows and file
modes, excluding version and prose documentation. If a code/test change is made
after the RC test, rerun affected validation and issue a new candidate. Public
bootstrap smoke runs directly after publishing (including when the Actions token
suppresses other workflow triggers), and can be dispatched independently. It
fetches the public main bootstrap and published assets, verifies/extracts them,
and invokes version/help; it never provisions an Ubuntu runner as a Steam Deck.
A failure after publication must be investigated; it cannot retroactively erase
a published release. Test the RC public path before promoting stable.

## Physical return checklist

Return PASS/FAIL/NOT_TESTED, the exact release/commit, Deck model, SteamOS/build,
kernel, Decky/plugin versions and sanitized command outputs for each row:

- [ ] T01 fresh Desktop Mode bootstrap; selected items install and verify.
- [ ] T02 second and third run: no duplicates; healthy state/configuration preserved.
- [ ] T03 previous stable upgrade: Android data, Docker data, CSS, templates,
  shortcuts, model/auth configuration and storage paths preserved.
- [ ] T04 interrupt an ordinary user-space download with Ctrl+C; resume succeeds.
- [ ] T05 targeted repair on a spare/test environment; orphaned Decky plugin
  folders must not count as a working loader. Do not delete production data.
- [ ] T06 SteamOS update followed by compatibility, health, Desktop and Game Mode.
- [ ] Reboot, open selected apps, load selected Decky plugins, inspect CSS visually.
- [ ] Confirm storage reports the intended card and UUID, including optional absent cards.
- [ ] Review support ZIP for secrets; confirm diagnostics remain available after failure.
- [ ] Test exact public candidate command; attach bootstrap and checksum results.

Do not factory-reset this Deck or manufacture destructive failures just to fill
this checklist. Fresh-install and destructive recovery evidence belongs on a
spare/reset-authorized device. No such destructive action is authorized by these
instructions.
