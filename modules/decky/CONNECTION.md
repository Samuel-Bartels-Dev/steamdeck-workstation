# Shared CSS Loader connection

Guided setup has one **CSS Loader connection** prerequisite before the selected
CSS themes and palette/recovery profile. If that connection cannot be established,
it reports `NEEDS_SETUP`; dependent items wait as `BLOCKED`, and independent
application installations continue. A component-specific failure after connecting
still belongs to that component rather than blocking unrelated themes.

Choose **Retry** on the connection item, follow its specific diagnostic, then
**Resume** to continue the saved queue. Retrying one theme also checks its connection
prerequisite. Completed, still-verified items are retained. A previous successful
connection record never substitutes for a current read-only backend check.

Setup reuses the installed CSS Loader API when available. Otherwise it tries live
activation through Steam's existing Decky connection. Steam debugger discovery
also tries IPv6 loopback after an IPv4 connection failure. This is a compatibility
fallback, not a diagnosis of every reported connection failure. A raced
already-enabled response is accepted only after server-state verification and
successful native backend probes.

Diagnostics distinguish missing plugin contracts, unreadable backend responses,
wrong theme directories, unavailable Steam context, transport failures and plugin
activation failures. Raw debugger payloads and third-party exception text are not
included in these messages. Standalone Backend instructions are no longer appended
to every shared-step failure regardless of cause.

Normal Desktop Mode does not require Big Picture, Gaming Mode or a terminal.
If live activation is unavailable, setup uses the installed upstream `SERVER`
flag contract and a controlled Decky restart. The existing KDE administrator
authorization dialog is requested only when this fallback is needed. The flag
created by setup lives until the queue exits, then is removed before a closing
restart, including on failure or normal cancellation. Existing flags and stored
settings are preserved. Cleanup failures are reported; abrupt termination cannot
guarantee cleanup.

Nested Desktop can use an existing/live backend but never uses the restart
fallback. It defers that connection with `NESTED_DESKTOP` before authorization,
writes or restarts. Other installations and saved completed work remain intact.
Review, status and verification are read-only and never enable the backend.
Malformed responses and unsupported plugin contracts fail without repair.

Selecting only the CSS Loader plugin does not add a theme connection step.
Recoloring supported themes that are already installed adds the connection check
without reselecting or downloading plugins.

## Regression coverage

Run `python3 tests/contract/test_css_connection.py` and
`./bin/deckctl repo validate`. The focused suite is also included in both Python
versions of the existing validation workflow. It uses mocked provider interfaces;
physical Steam Deck and Game Mode acceptance remain separate from CI.
