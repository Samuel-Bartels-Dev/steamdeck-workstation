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
