# Setup layout and continuous-output refinement

This pass retains the existing Qt/QML and Python architecture. Two independent,
read-only UI and test-coverage investigations preceded the changes; a separate
validation reviewer inspected the final diff. The earlier
[architecture decision](../../UI-INSTALLER-AUDIT.md) remains applicable: this work
addresses layout and interaction defects, not a measured need for a new framework.
No installer providers, authentication workflows, or user configuration were
replaced. No additional runtime dependencies or background services were added.

## Findings and changes

| Priority | Finding | Implementation |
| --- | --- | --- |
| P1 | Details replaced the overall record with an item log, stopped combined updates, and was absent for scheduled items without logs. | [Setup.qml](../../../lib/deckctl/ui/Setup.qml), `showLog`, `applyConsole`, `markerIndex`: Details jumps to an exact line-start item marker in one ordered record. Waiting items stay selected until output arrives. New output continues while the viewport stays in history. |
| P1 | The 64 KiB snapshot could hide the beginning of an otherwise retained whole-run log. | [setup_window.py](../../../lib/deckctl/setup_window.py), `Session.console`: read the current run's bounded live record, then the identical archived record. Paths derive from a validated run ID, reject symlinks, and never stitch item logs together. [setup_process.py](../../../lib/deckctl/setup_process.py) marks snapshot truncation. |
| P1 | Long dialog content and larger fonts could clip actions or overflow the scroll viewport. | Shared fitted/message dialogs, wrapped actions, dynamic checkbox/banner height, fixed dialog actions, explicit drawer insets, and actual scroll-viewport widths in [Setup.qml](../../../lib/deckctl/ui/Setup.qml). Focused controls scroll into view. |
| P2 | Scheduled/completed rows and logs competed with immediate activity evidence. | Deck Activity precedes Output Console. The queue starts collapsed with attention, scheduled, and completed counts. Active work and pause/cancel controls remain independent. Expansion and item details survive refresh/collapse. |
| P2 | Flat inventory order buried failures and repeated lengthy details. | `statusGroups` groups attention, updates, unknown/checking, installed, and optional missing tools; names sort alphabetically within groups. Details expand per item and retain state. Missing optional tools are neutral. Missing-password guidance takes priority; healthy system facts are below the groups. |
| P2 | Late console callbacks could overwrite newer selections; rotation could select unrelated text or leave the viewport blank. | Record/navigation checks preserve newer interaction. A new source or rotated record clears old offsets and resets the viewport. A recovered read clears its warning. Next error highlights within the full record rather than filtering it. |

The console remains a read-only diagnostic viewer. Explicit interactive vendor
and credential entry still use their existing labeled handoffs. Existing
redaction, private logging, retention, and cancellation ownership boundaries are
unchanged. A failed canonical read preserves the displayed record and reports the
failure. When only the live snapshot is available, or the retained head has been
removed, the UI explicitly describes the limit instead of claiming completeness.

## Rendered evidence

These are real offscreen Qt renders of synthetic fixtures, not live installs.
The long-text fixtures use **1.35× actual font metrics in the same logical window**,
not merely display DPI scaling. Normal UI text remains at its current scale;
`textScale` is a bounded presentation/testing property (1.0–1.35).

| Before | After |
| --- | --- |
| ![Previous install screen at 800 by 600](before-install-800.png) | ![Activity before overall console at 800 by 600](after-install-800.png) |


Additional views below demonstrate different states, rather than before/after comparisons.

| Long content and status | Continuous output and queue |
| --- | --- |
| ![Appearance with larger text and fixed Close at 760 by 540](appearance-760.png) | ![Collapsed queue with counted sections](queue-collapsed-760.png) |
| ![Appearance bottom reached by keyboard, with fixed Close](appearance-bottom-760.png) | ![Selected item highlighted within the overall console](console-760.png) |
| ![Grouped status with inset content and fixed Close](status-760.png) | ![Scheduled item waiting for output in the same console](console-waiting-760.png) |
| | ![Expanded counted queue](queue-760.png) |

![Steam Deck-sized view with enlarged text and wrapped sidebar](sidebar-1280.png)

## Automated validation

Repository validation passed: **17 modules and 343 tests across 19 suites**.
Targeted backend contracts passed: **25 window tests** and **42 setup-experience
tests**. The focused Qt test passed at 1280×800 and 760×540 with 1.35× text,
long labels/paths, all setup stages, nested CSS/plugin pages, every dialog,
Appearance Tab/Shift+Tab traversal, modal focus restoration, pointer queue/Details
activation, stable status grouping, and continuous-output transitions. The
existing four-size rendered flow and real-keyboard test remain in the same
[test runner](../../../tests/integration/test_setup_ui.py). The focused fixture is
[setup_layout.qml](../../../tests/integration/setup_layout.qml).

The final no-screenshot Qt suite passed **3 tests in 19.558 seconds**, including
the four-size flow and genuine keyboard test. Final rendered confirmation passed both enlarged-text
sizes in **8.472 seconds**, including outer-console visibility, highlighted-output
geometry, late error jumps after record replacement, and queue captures. Lint
passed **82 Python files, 70 shell files, and 5 workflows**, including documentation
checks. Independent read-only review found no remaining blocking findings.
Final CI and package results are recorded separately in the PR.

Qt 6.4 requires the deferred TestCase start gate: catalog loading alone can start
tests reentrantly. Focus tests observe stable visible bounds within one second;
they do not move focus or scroll to make an assertion pass. Actions avoid a
parent-dependent maximum-width constraint that produced a Qt 6.4 layout polish
warning; the corrected Qt 6.4 CI run passed all three tests without that warning.
Focus reveal stops after at most eight timer ticks, and explicit console
navigation cancels it.

Nonmodal screenshots use a warmup render, passive stable-geometry checks, and a
final render whose queue geometry must remain unchanged. This synchronizes the
image with the measured scene; an earlier unsettled image alone was not proof of
runtime clipping. Modal screenshots include the window overlay. Fresh screenshot
output directories are created automatically. Physical input remains unverified.

A bounded near-cap stress fixture retains about 1,014,055 ASCII bytes, appends a
line, locates the last error, and sends real keyboard input. Its observed combined
apply/append/input time was 548–674 ms including intentional waits on this host.
A separate near-cap microbenchmark observed initial loads around 1.6–2.1 seconds;
results vary with concurrent work and fixture state. Append-only updates use
`TextArea.insert` without adding or changing newline bytes, avoiding unnecessary
whole-document replacement. These samples are not an FPS benchmark or a proven
performance improvement. A large initial log or replacement can remain noticeable;
no Rust component or framework migration is justified by this evidence.

## Physical acceptance still required

Run this checkout, rather than an older installed release:

```bash
cd /home/deck/Projects/steamdeck-install-controls
./bin/deckctl setup customize
```

Return this checklist with window size, SteamOS version, and any screenshot/log
for a failure. The checks below do not require installing additional tools unless
you intentionally select and start an installation.

- [ ] At 1280×800 and a smaller window, every dialog has a visible action footer.
- [ ] Appearance's last preference and explanatory text can be reached; Close remains visible.
- [ ] Steam Input controller mappings and Tab/Shift+Tab reach choices, long-list rows, and dialog actions without trapped focus.
- [ ] Deck Activity precedes output; pause/cancel stay usable during a real provider operation.
- [ ] A collapsed queue has correct counts; expanding it preserves the selected row across updates.
- [ ] Details on a scheduled item shows waiting context, then highlights its first real step without losing other output.
- [ ] Scrolling/selecting old output does not jump to the bottom on the next poll. Next error keeps surrounding output.
- [ ] A real failed/paused/resumed run retains its durable log and accurate item state.
- [ ] Status groups separate missing optional software from failures and retain expanded details after refresh.
- [ ] Long sessions, on-screen keyboard, touch, Steam Input, nested Desktop Mode, and actual network/storage changes remain usable.

Offscreen keyboard simulation does not prove raw controller mappings, touch,
on-screen-keyboard behavior, real provider throughput, or physical install/repair
outcomes. No live installation, password entry, or personal configuration was
performed to produce this report.
