# Setup sharing and installation experience

Implement the user's five requested improvements: complete portable setup choices;
read-only installation preview with dependencies, update state and storage estimates;
per-item persistent progress and targeted retries; palette swatches and honest Game
Mode theme previews; and a finish screen with launch, sign-in and pairing actions.
Physical Steam Deck usability acceptance is reserved for the user.

Keep vendor installers and authentication in their existing module boundaries.
Never install real apps/models or change the user's Game Mode while testing.
Preserve all saved choices and credentials. Preview/import must not install software.

Implementation: complete setup export/import preview, dependency and update/space
preview, on-demand item runner with persisted resume/retry, CSS palette swatches
and labelled menu/keyboard illustrations, upstream preview gallery link, and
finish actions with detected versus user-confirmed readiness.

Validated locally: full repository suite (17 modules), native CSS partial apply
and recovery profile tests, setup experience contracts, Ruff/ShellCheck/actionlint,
documentation checks and real Qt flows at 1120×720, 800×600 and 760×540.
No real vendor installs or Game Mode appearance changes were performed.
Physical hardware acceptance remains with the user; GitHub PR checks follow.

Installer follow-up: app-owned sudo temporary tickets must retain one parent and
session across Install/Retry/Resume and supported provider children, with no
password transport or persistent NOPASSWD rules. The app lifetime supervises
authorization and foreground queue processes, including renderer/crash cleanup.
Android uses the shared queue and preserves upstream image/storage/protected
repair checks; adapted provider files require exact reviewed contracts. Installed
Android launchers also need temporary GUI authorization after setup closes.
Nested Desktop must defer Android and any Decky restart before mutation.

Read actual supplied/recent hardware logs: the current CSS failure is the selected
shine theme's exact Store name; profile is correctly blocked. Reuse PR #58's fix.
Older connection failures predate merged PR #57; read-only checks currently have
no live CSS backend. Preserve completed components, native settings and selection.
Safe validation uses fake sudo/process fixtures and read-only upstream/Store
inspection. KDE prompts, Android GUI/sign-in and physical Deck acceptance remain
hardware checklist items; never report these as physically tested.
