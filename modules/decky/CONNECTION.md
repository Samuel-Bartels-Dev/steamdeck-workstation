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

Opening Steam Big Picture or changing a CSS Loader setting may still require a
user action when the live connection is unavailable. Setup does not switch
sessions, restart Decky/Steam, request sudo for CSS, retrieve authentication tokens,
connect another Decky frontend socket or install Python packages. Review, status
and verification never enable the backend or mutate theme settings.

Selecting only the CSS Loader plugin does not add a theme connection step.
Recoloring supported themes that are already installed adds the connection check
without reselecting or downloading plugins.

## Regression coverage

Run `python3 tests/contract/test_css_connection.py` and
`./bin/deckctl repo validate`. The focused suite is also included in both Python
versions of the existing validation workflow. It uses mocked provider interfaces;
physical Steam Deck and Game Mode acceptance remain separate from CI.
