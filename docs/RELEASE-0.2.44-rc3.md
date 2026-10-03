# Steam Deck Workstation 0.2.44-rc3

Includes all 0.2.44-rc2 installer, temporary authorization, Android and CSS fixes,
plus automatic non-Steam Gaming Mode shortcuts for selected Discord, Parsec,
Spotify, Slack and ChatGPT installs.

The four desktop apps launch their installed Flatpaks. ChatGPT uses its existing
persistent Chrome app-window runner and profile. Installation, module apply and
the setup queue all reconcile shortcuts; existing exact Steam app targets are
reused even when renamed. Saved choices, app data, custom Steam arguments,
artwork and existing ChatGPT launcher/profile settings are preserved.

Shortcut submission uses SteamOS's existing helper with its Steam URI fallback.
Steam must already be open and signed in. Setup does not start/stop Steam or
switch sessions, including Nested Desktop. Shortcut-only Retry/Resume reuses
installed packages without updating or reinstalling them.

Steam may delay saving a shortcut. Until an exact account-scoped VDF record is
found, the app reports pending confirmation and the queue keeps the item
retryable. Same-session receipts prevent repeated submissions. A failed helper
is retryable; a canceled or timed-out handoff remains unconfirmed until Steam
saves it or you manually restart Steam, after which a missing target can retry.
Verification and status never submit shortcuts or alter Steam records.

Regression coverage uses fake Steam helpers/accounts, isolated Flatpak state and
mocked queue operations: selection, exact target matching, renamed shortcuts,
account scope, concurrent submissions, target changes, helper failure,
cancellation/timeout, manual Steam restart, read-only status, package failure,
existing app reuse, ChatGPT profile preservation and Resume of old DONE items.
Read-only hardware inspection confirmed installed apps and the native helper;
physical launch, login, audio, remote streaming and controller behavior still
need user acceptance. Candidate status retains the outstanding hardware matrix.

Existing installations can reconcile selected Flatpaks with
`deckctl apps install discord parsec spotify slack`. For selected ChatGPT run
`deckctl workspace setup`, or choose Retry/Resume in the setup app. Refresh Steam
when convenient and check its non-Steam library; setup never forces that refresh.
