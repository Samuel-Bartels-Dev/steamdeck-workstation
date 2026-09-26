# Production diagnostics and release validation

This engineering pass adds foundations; it does **not** certify this release on
fresh hardware. See [the inspection and gap analysis](PRODUCTION-READINESS-REVIEW.md)
and [existing hardware checklist](HARDWARE-TESTING.md).

## Installed runtime versus development source

Permanent installations keep the CLI, QML UI, libraries, modules, configuration,
compatibility records, companion-host payloads, licenses, user documentation and
installation/support helpers. Tests, Git history, CI workflows, AI adapters,
development task notes and build/lint tools stay out of the installed runtime.
No developer checkout is needed to use or update `deckctl`.

The downloaded release/USB archive still contains source and tests. Its existing
full regression gate runs before the lean copy is promoted. This change reduces
permanent installation content, not the release download size. Source checkouts
continue to run the full suite with `deckctl repo validate`.

On an installed runtime, that command explicitly reports **RUNTIME INTEGRITY PASS**:
file hashes, modes, required files and module action targets match its generated
manifest. It does not claim to run development regression tests. The manifest
checks accidental damage; it is not a signature or substitute for release checksums.
Updates and rollback retain their existing versioned-directory/link mechanism.
Existing older full installations are retained for rollback, not automatically pruned.
Developer commands such as generating project tasks require a source checkout.

## Commands and state

Normal UI **Install**, **Resume**, and **Retry** run directly with an inline live
output panel, without opening Konsole. The viewer reads the redacted, bounded
whole-run record (up to 1 MiB), including its durable archive after completion.
The private 64 KiB `setup-console.json` record remains a fallback; missing or
truncated history is explicitly labeled. **Following latest** controls scrolling,
while the same ordered record continues updating. **Details** highlights an exact
item marker without replacing the record. **Next error** highlights the next
matching line; it never filters away surrounding context.

The install screen puts measured Deck Activity before the overall console. Active
work stays visible independently of the queue, which starts collapsed with counts.
Expand it for attention-needed, scheduled and completed items. Details is available
even before an item starts and waits for its first output marker.
**Pause after item** finishes the current item before waiting at the next boundary;
**Continue queue** releases that pause. **Cancel run** interrupts the owned installer
process group. After ten seconds, a separately confirmed **Force stop** can end an
unresponsive provider. This can leave the current item incomplete: resume verifies
completed items and retries unfinished work. Cancellation does not uninstall apps.
Closing an owned active run offers cancellation and closes after the worker exits.
A viewer of a run started elsewhere can close, but must use the originating window
or terminal to cancel that run. Unexpected renderer closure gracefully cancels its
owned process group, then applies bounded escalation if the provider ignores it.

Network receive and disk read/write graphs use Linux sysfs counters, sampled only
while a run is active. They include other applications on the Deck, exclude virtual
devices to avoid double counting, and show unavailable counters as gaps. They are
not per-download byte measurements. The rolling history is limited to 60 samples;
no monitoring daemon is installed. Separate scales and real timestamps make
network and disk activity comparable over time without sharing a misleading axis.
Zero traffic is not offline. Physical carrier evidence distinguishes link available,
offline and unknown, without claiming Internet reachability. Stale readings and
completed-run rates are labeled accordingly. Provider progress remains separate.
GitHub API exhaustion is a preflight warning with reset time and retry instructions.
Independent items can continue; an item that requires the unavailable API must still
complete its own download and verification. Failed items remain retryable and their
dependents remain blocked. Other preflight safety failures still block the run.
The install screen shows a countdown and local reset time from the latest recorded
GitHub preflight response. The timer makes no API calls and never auto-retries installs.
When it expires, the UI invites a retry without claiming availability was rechecked.

Known interactive vendor/privileged providers are deferred when they do not
already verify. They show **Continue in terminal** after the pass, rather than
attempting to collect input through the output panel. Finish checks readiness in
the UI; only explicitly selected interactive setup/authentication actions use Konsole. This preserves vendor wizards and password prompts; normal UI
workers have disconnected stdin and no controlling terminal. A failed unexpected
prompt can be retried explicitly in a terminal. No terminal opens automatically
for a normal install/resume/retry.

The **Deck status** / **Setup check** button opens detailed inventory and password
guidance in a drawer. App cards retain short status labels; detailed version/check
information is available in the drawer and hover tooltips. **Appearance** in the
sidebar still controls the shared palette and selected appearance targets.
The ready-to-install view stays minimal until an operation starts. Results use
compact expandable rows instead of a card per item. Running and unfinished work
comes first; completed rows can be shown during a pass. Select a result to reveal
its diagnostics and retry/interactive actions.

Setup reopens with a summary of its last saved installation when the plan and
installer version still match. **Resume installation** re-verifies completed
items before skipping them; **Review choices** edits the plan without starting
anything; **View last results** displays the recorded outcomes. If the plan or
version changed, old results are not presented as proof for the new plan. A live
installation opens its progress view instead of launching another installer.

Fresh setups show an optional four-step guide: Desktop Mode, password readiness,
storage, and choosing/reviewing apps. Skip it any time, or reopen it through
**More → First-run guide**. The guide does not select components or save settings.

Before installing from review, **Review changes** checks the selected plan and
groups new installs, updates, configuration and existing-installation checks.
It includes dependencies, available download estimates, and known privilege and
restart guidance. Unspecified vendor requirements remain explicit. After reading
the results, **Save & install** confirms the operation. Known insufficient space
blocks that confirmation; unknown sizes are still estimates, not a capacity
guarantee. Changing selections invalidates the preview. Saving for later remains
available without network checks.

Final item results distinguish reported installs, updates and already-current
apps. Providers that do not report the action receive **Verified**, rather than
a guessed update result. Each result includes its next action; use **Recheck
readiness** for current sign-in/pairing/setup follow-up. Last-run results describe
that attempt, not continuous monitoring of the installed software.

On a fresh or reimaged Steam Deck, setup and preflight inspect the current account's
password status with `passwd --status`. If missing or locked, the UI explains how
to open Konsole and run `passwd`, then offers **Recheck password**. Password typing
is intentionally invisible in the terminal. No password is collected by the UI,
logged, or passed as a command argument. An unavailable check is a warning, not a
claim that a password exists. User-space installs remain available; installers
requiring administrator access still authenticate through their normal prompts.
A set password does not prove sudo policy authorization; `sudo -v` in Konsole can
check that explicitly. The automatic check never runs an authentication prompt.

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

Opening the setup UI starts a read-only background inventory, including options
you have not selected. Cards show installed, not installed, needs setup, and
update status. Supported update providers distinguish **Update available** from
**Up to date**; unavailable or unsupported checks remain explicitly unknown.
System-managed Flatpaks are identified separately. These checks never select
options or install updates for you. Use **Refresh status** to check again; the UI
also refreshes when an installation finishes.

Cards include the check time and installed → available versions when the provider
exposes them. Flatpak versions are compared by immutable commit; shortened hashes
are labelled as commits. **Select updates** adds available updates to your choices
without removing existing selections or starting an installation. Review the plan
before saving and installing.

**Details** jumps to an item in the single copyable overall console and keeps its
highlight while new output arrives. Failed/interrupted items can be retried after
the current operation finishes. Whole-run and per-item logs retain at most 1 MiB
each; older markers may be outside that bounded history. The viewer does not stitch
per-item logs together or imply that unavailable history is complete. Phase events
and UI provider stdout/stderr are available here; explicit
interactive vendor stdout/stderr and input stay in the requested terminal and are
not captured as unattended raw logs. This is a diagnostic viewer, not an embedded terminal.

Every running item shows elapsed time and time since its last progress event or
log write. After 90 seconds without activity, setup says possibly stalled or quiet and
suggests inspecting the console before cancellation or retry. Silence alone neither fails the item nor proves it is waiting for
input. Quiet extraction or vendor buffering can produce the same symptom.

Resume re-verifies previously completed items before skipping them. Interrupted
or failed items are retried through their existing provider. Automated tests inject
interruption and extraction failure into the runner; they do not certify every
vendor's recovery after a reboot or power loss.

During Flatpak operations, the UI distinguishes checking, installing, updating,
and already-current results. When Flatpak supplies progress, its percentage,
speed and ETA appear in the current step. These are Flatpak transaction progress,
not an invented byte count or overall installer percentage. Other providers may
still offer less detailed progress. UI changes take effect on the next launch.

The established project state root remains `~/.local/state/deckctl`, overridable
with `DECKCTL_STATE`. Each CLI setup-install/apply/update-apply, explicit repair,
and SAFE test has a unique private directory under `logs/` with:

* `result.json`: operation, version, exit status, run ID and duration.
* `events.jsonl` and `run.log`: correlated events.
* `plan.json`: installation/preflight plan or SAFE test result where applicable.
* Hashed `.log` files: bounded item diagnostics; UI runs also archive combined
  stdout/stderr including preflight. Explicit interactive authentication output is
  excluded. The ordinary CLI retains its stdout/TTY behavior.

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
