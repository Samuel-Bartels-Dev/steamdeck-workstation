# Installer UI and architecture audit

Date: 2026-09-26. Baseline: `034537a` / `5aa5ba7`, version `0.2.44-rc1`.
Three independent, read-only investigations covered usability, installer/process
ownership, and compatibility before implementation. Their recommendation is to
retain **Qt Quick/QML with Python**, preserving the existing provisioning engine.
No Rust component, framework migration, or framework proof of concept is justified
by the measurements collected here. Appearance changes do not require a rewrite.

## Prioritized findings and implementation

| Priority | Finding and source | Resolution |
| --- | --- | --- |
| P1 | The normal finish button launched blanket `setup run` in Konsole. The generated Continue shortcut did the same. `setup_window.Session.start`, `core.create_setup_shortcut`, `ui/Setup.qml`. | Finish checks readiness inside the UI. Continue opens the installed setup UI. Docker uses the selected-item captured runner. Only explicitly labeled vendor/CLI authentication handoffs open terminals. Existing desktop files change on the next shortcut provisioning pass. |
| P1 | Item logs captured stderr only; stdout could survive solely in the overwritten 64 KiB UI console. `install_log.capture`, `setup_process.start`, `production_cli.operation`. | UI runs capture stdout and stderr into private bounded item logs and a combined run archive, including failed preflight. Structured events and console phase/result headings identify item/module and step. The first validated run header identifies the current log even when preflight fails before a new item journal exists. |
| P1 | Closing/crashing the QML renderer could leave its installer running. `setup_window.launch`, `setup_process.Handle`. | Renderer exit gracefully cancels its owned process group, allows a bounded cleanup period, then escalates. Completed work remains; interrupted items are rechecked on resume. Descendants in the owned group are cleaned up. Separate systemd services and unrelated processes are not targeted. |
| P1 | Output was below queued rows and a second modal held item logs. Controls scrolled away. `ui/Setup.qml`. | One scrollable console precedes queued results. Item logs use the same surface. Error-keyword search retains nearby context; verified result status remains authoritative. Pause/cancel controls remain outside the scrolling content. History viewing freezes the display while collection continues. |
| P2 | Small windows lost width to a persistent sidebar and height to decoration; diagnostic text was small. `ui/Setup.qml`. | Compact section selector below 950 px, reduced install header, 13 px diagnostic text, visible focus outlines and accessible control labels. Actions stay keyboard reachable. |
| P2 | Network and disk shared an unlabeled scale; zero traffic and missing counters were easy to misread. `setup_activity`, `ui/Setup.qml`. | Separate network and disk charts use actual timestamps and measured rates, with independent scales and gaps for missing/stale samples. Carrier state explicitly distinguishes offline/link available/unknown. Link availability does not claim Internet reachability. |
| P2 | Disk checks lacked an understandable visual budget. `setup_plan.preview`, `setup_activity.storage_status`. | Destination, measured free space, existing staging allowance and 1 GiB reserve feed a space meter. Unknown sizes remain unknown. Live comparisons use the original allowance, not a fabricated remaining-size estimate; they do not abort an active provider. |
| P2 | QML progress requests could overlap; quiet vendors looked stuck. `Setup.qml` timers, `setup_window._progress`. | One in-flight progress request, independent process controls, download bytes/totals when provided, indeterminate progress otherwise. At 90 seconds without output, the UI says possibly stalled or quiet, without inventing failure. |
| P2 | README called the USB archive an offline install without explaining provider downloads. Runtime presence alone did not explain missing QML imports. `README.md`, `setup_window.launch`. | Offline control-plane prerequisites are explicit. Renderer errors use a bounded 16 KiB memory tail and name required QML imports/display context; no system package changes. |
| P3 | `Setup.qml` remains a large file and GUI dependencies are inherited from SteamOS. | Reusable chart/budget components reduce repeated display logic. Further file extraction and release compatibility work should be incremental, with contract and real Qt coverage. A new framework does not remove these responsibilities. |

Source map: [QML window and controls](../lib/deckctl/ui/Setup.qml),
[Session/HTTP and renderer lifecycle](../lib/deckctl/setup_window.py),
[process/output collector](../lib/deckctl/setup_process.py),
[item capture](../lib/deckctl/install_log.py),
[whole-run CLI wrapper](../lib/deckctl/production_cli.py),
[durable run retention](../lib/deckctl/run_log.py),
[queue and provider execution](../lib/deckctl/setup_install.py),
[finish actions](../lib/deckctl/setup_finish.py),
[activity and storage measurements](../lib/deckctl/setup_activity.py),
[plan budgets](../lib/deckctl/setup_plan.py),
[generated desktop entry](../lib/deckctl/core.py).

Changes preserve desired
state, provider commands, verification contracts, atomic runtime packaging and
module ownership. Explicit interactive providers bypass raw archival capture:
their sign-in URLs, QR codes and peer output do not become unattended log payloads.
CLI stdout/TTY behavior is preserved; structured results remain available.

## Evidence before choosing a language

Measurements were taken on the existing implementation, before these changes:
Steam Deck OLED/Galileo, SteamOS 3.8.16, Python 3.13.5, Qt 6.9.1, glibc 2.41.
This is one development device, not a clean-install compatibility certification.
Raw samples: [baseline measurements](reviews/ui-installer/baseline-measurements.json).

| Measurement | Observation | Interpretation |
| --- | --- | --- |
| Catalog, 5 local reads | Median 55.41 ms; max 64.18 ms | No demonstrated CPU bottleneck requiring native code. |
| Progress, 10 local reads | Median 80.16 ms; max 82.87 ms | Polling/status work is small relative to the previous 1.5 s UI poll interval. |
| 250 sysfs activity reads | Median 0.536 ms; p95 0.826 ms; max 1.275 ms | Reading counters does not justify a Rust helper. |
| Real HTTP pause/continue while catalog blocked, 30 requests | Median 1.378 ms; p95 1.75 ms; max 1.79 ms | Threaded request handling already isolates controls from a slow status request. |
| Synthetic 4 MiB / 32,768-line output flood, 3 runs | 0.784–1.177 s; 64 KiB tail retained, final line present | Log parsing throughput, **not download bandwidth**. CPU cost warrants batching if real vendors produce similar sustained floods. |
| Paced output visibility, 26 observed samples | Median 209.51 ms; max 419.33 ms | 20 ms observation polling; excludes QML's poll delay and rendering. Final four generated samples were not included. |
| Cooperative synthetic child cancellation, one trial | Acknowledgement 0.5 ms; exit 29.3 ms | Proves the control path works, not that all vendor installers stop that quickly. |

These are small local samples, not renderer FPS, end-to-end latency, memory/RSS,
GPU utilization, battery life or framework comparisons. No Rust benchmark was
performed, so this review claims no Rust speed or memory advantage. Network and
vendor downloads, subprocess behavior, repeated probes and UI layout are the
observed architecture concerns. Qt itself recommends measuring before optimizing
and keeping blocking work off the GUI thread. [Qt Quick performance guidance](https://doc.qt.io/qt-6/qtquick-performance.html).

## Three implementation options

| Criterion | Improve Qt/QML + Python — recommended | Small measured Rust helper | Rust desktop framework migration |
| --- | --- | --- | --- |
| SteamOS packaging/dependencies | Current user-space release remains Python + host Qt Quick. No pacman or root filesystem changes. Fresh SteamOS must still validate required imports. | Keeps Qt/Python and adds a versioned binary, protocol, architecture and libc/ABI checks. Adds a Rust build/security toolchain. | Tauri adds a web frontend plus Rust and Linux WebKitGTK/GTK requirements; AppImage can bundle dependencies but needs base-system validation. Native Rust UI choices such as Slint have different renderer/backend dependencies. |
| Offline installation | Local control plane can install from release/USB when host dependencies exist. Apps/plugins/models still require cache or network. | Same provider limitations, plus helper must be shipped in release rather than fetched at runtime. | Must bundle or otherwise deliver compatible runtime libraries/assets offline. Moving framework does not bundle vendor payloads. |
| Output capture | Existing pipes, process groups, durable journals and bounded readers can meet the requirements. This change addresses actual capture gaps. | Could own a measured high-volume stream parser; still requires redaction, grouping, lifecycle and protocol tests. | Backend/sidecar still must own pipes, interactive boundaries, cancellation and logs. New webview IPC adds a boundary, not automatic correctness. |
| Responsiveness | Existing threaded HTTP controls measured responsive under blocked status. Keep probes off critical paths and bound polling/output. | Useful only if profiling shows sustained CPU-bound parsing; no such real workload was demonstrated. | Cannot assume improved rendering/memory. Must measure on Deck; webview or native-renderer behavior differs. |
| Maintainability | One existing engine, existing tests and familiar Python providers. Incrementally split QML display components. | Two languages, build systems and a stable IPC/schema boundary for one component. | Tauri usually also introduces HTML/CSS/JS or TypeScript, plus Rust. A native framework requires a new UI/control/accessibility model. Installer reuse is safer than an engine rewrite. |
| Migration effort | Bounded, reviewable changes in existing modules and UI. | Medium: isolated API, serialization, artifact delivery and failure compatibility. | High: UI, lifecycle, accessibility, state compatibility, installer bridge, packages, CI and hardware acceptance. |
| Regression risk | Lowest: same provider and persistence contracts; new regressions tested at boundaries. | Medium: duplicated state/error semantics and binary delivery risks. | Highest: every navigation, authentication, process, installer recovery and hardware interaction needs revalidation. |

Packaging facts: [Tauri Linux prerequisites](https://v2.tauri.app/start/prerequisites/),
[AppImage distribution](https://v2.tauri.app/distribute/appimage/),
[sidecar binaries](https://v2.tauri.app/develop/sidecar/),
[Slint backends/renderers](https://docs.slint.dev/latest/docs/slint/guide/backends-and-renderers/backends_and_renderers/),
[Rust target/platform support](https://doc.rust-lang.org/rustc/platform-support.html).
The inspected Deck exposes Qt libraries; WebKitGTK was absent from its linker cache.
That observation does not prove every SteamOS image lacks WebKitGTK, nor that a
bundled Rust framework is impossible.

A helper should be reconsidered only after profiling a repeatable real workload
that misses a defined response budget, then comparing a bounded helper prototype
with a Python batching fix on the same workload. A full migration needs a separate
reviewed plan and Deck proof of concept covering packaging, input/accessibility,
process ownership and state compatibility. Neither gate is met today.

## Validation and visual evidence

Regression additions cover stdout/stderr archival, split secrets/ANSI/Unicode,
private interactive handoffs, failed preflight correlation, bounded renderer
errors, captured Docker routing, Continue shortcut routing, renderer crashes,
ignoring grandchildren, carrier states and unknown/insufficient storage.
The Qt integration suite exercises selection, review, finish, error search,
retained history and renders 1280×800, 1120×720, 800×600 and 760×540 fixtures.
Qt 6 Test sends real Space/Tab/Shift+Tab/Escape key events rather than only calling
click handlers. This Deck also has a generic `qmltestrunner` linked to Qt 5;
the test explicitly selects Qt 6's runner. CI installs the QtTest module as a test
dependency, not a runtime requirement for the installer. Ubuntu CI's Qt 6.4.2
exposed test-harness reentrancy: its `TestCase.onWhenChanged` invokes `qtest_run()`
synchronously. A `when: app.loaded` condition therefore entered the keyboard test
inside the catalog callback, before that callback scheduled the first-run guide.
Waiting inside that test could not finish the interrupted callback. The Deck's
Qt 6.9.1 instead queues tests through `TestSchedule`, explaining the local pass.
The harness now starts from a one-shot Timer after loading/window display, on a
new event turn, then asserts modal, active-window and focus readiness. No key
assertion or automatic-guide check was removed. This is a test-only correction;
CI must confirm it on Qt 6.4.2.
[Qt 6.4.2 TestCase source](https://github.com/qt/qtdeclarative/blob/v6.4.2/src/qmltest/TestCase.qml),
[Qt 6.9.1 TestCase source](https://github.com/qt/qtdeclarative/blob/v6.9.1/src/qmltest/TestCase.qml).
Tests do not install vendor software, change personal palettes or open auth flows.

Validation: the full repository build passed validation for all 17 modules and
built the release archives successfully. Lint passed for 82 Python files, 70 shell
files and 5 workflows, including documentation checks. All 42 setup-experience
contracts and 5 install-appearance contracts pass. The existing CLI phase-log
regression was fixed without changing baseline fixtures or guard allowances.
Real Qt integration and keyboard tests pass at all four sizes (2 tests, 15.445
seconds in the final UI run). Independent review found no remaining blocking
findings. Final verification of the extracted release archives is recorded in
the draft PR; it was still running when this report was updated.
Before/after images are synthetic installer scenarios rendered by real Qt; they
are not evidence that a live vendor install or raw controller navigation passed.

| View | Before | After |
| --- | --- | --- |
| Install, 1120×720 | [Before](reviews/ui-installer/before-install-1120.png) | [After](reviews/ui-installer/after-install-1120.png) |
| Install, 800×600 | [Before](reviews/ui-installer/before-install-800.png) | [After](reviews/ui-installer/after-install-800.png) |
| Choices, 800×600 | [Before](reviews/ui-installer/before-choices-800.png) | [After](reviews/ui-installer/after-choices-800.png) |

The separate activity scales and space meter are shown at [1280×800](reviews/ui-installer/after-metrics-1280.png) and [760×540](reviews/ui-installer/after-metrics-760.png).

## Physical Deck acceptance checklist

This draft does not redeploy the installed `deckctl` runtime or reuse its version
with changed contents. Test this checkout explicitly:

```bash
cd /home/deck/Projects/steamdeck-install-controls
./bin/deckctl setup customize
```

- [ ] At 1280×800 and a small Nested Desktop window: text readable, no clipped actions;
  touch targets usable; Tab/Shift+Tab, Space, Escape and Steam Input/controller
  focus behave predictably. Traverse long lists and verify focused choices scroll
  into view. Long-list auto-scroll and raw controller input mapping remain
  unverified; the automated keyboard test covers only a few controls.
- [ ] Select an already installed app. Review shows evidence/current or update
  status without pretending unavailable online metadata is current.
- [ ] Install/update a selected noninteractive app. One console shows its module,
  phases, provider output and result. No extra terminal opens.
- [ ] While viewing older console text or charts, Pause after item and Cancel stay
  visible. Pause finishes the active item; resume starts the next. Cancel keeps
  completed work. Force stop is explicit after the grace period; retry verifies.
- [ ] With downloads active, charts show real receive/read/write activity. Rates
  include other apps. Zero traffic is not called offline. Loss of physical link
  shows Offline; a connected link does not claim Internet access.
- [ ] Review a large model with insufficient free space without installing it.
  Known allowance/reserve and shortfall are clear; unknown provider sizes remain
  unknown. Do not fill the filesystem intentionally.
- [ ] Finish opens readiness inside the UI. A vendor/auth row explicitly labeled
  interactive terminal opens one only when chosen. Cancelled password dialogs
  leave retries available; do not share passwords or sign-in output.
- [ ] Return run ID, affected item ID, screenshot, expected/actual behavior and
  relevant redacted log excerpt. Review logs before sharing.

Read-only checks from this checkout:

```bash
./bin/deckctl health --json
./bin/deckctl compatibility --json
./bin/deckctl logs latest
./bin/deckctl logs errors
```

Expect local health evidence, honest UNKNOWN for untested compatibility, and a
current run directory with structured events plus bounded detailed logs.
Warnings/configuration-required may exit 2; failed checks exit 1. A test renderer
or synthetic fixture passing is not a production release gate. Fresh SteamOS,
reboot, Gaming Mode theme application, real privileged vendors, SteamOS updates,
network interruption and previous-release upgrade preservation remain physical
acceptance work. Stable-release promotion is not recommended until those gates pass.
