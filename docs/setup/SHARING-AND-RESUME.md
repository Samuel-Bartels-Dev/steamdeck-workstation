# Share a setup and install only what you need

Choose apps, tools, launchers, Decky plugins and CSS components individually in
`deckctl setup customize`. Dependencies appear as included choices. Deselecting an
item leaves existing software and personal data in place.

## Share choices

Save your plan at Review. **More → Export saved setup** writes a portable ZIP.
It includes module, app, component, launcher, Decky, CSS/palette and appearance choices, plus
allowlisted captured configuration. Browser sessions, passwords and tokens are
excluded. The receiving Deck uses **More → Import setup**, reviews the included
files, confirms, then reviews or removes choices before installing anything.
Cancelling leaves its configuration unchanged. Import saves a rollback copy.

Terminal equivalents:

```bash
deckctl profile export --out ~/deck-setup.zip
deckctl profile import ~/deck-setup.zip
```

## Check downloads and space

At Review, use **Check changes & space**. Flatpak commit metadata and managed
terminal release versions distinguish checked updates from installed software
whose update state is unknown. Model manifests supply download estimates.
Offline checks remain unavailable rather than claiming software is current.
System Flatpaks are reused and managed through their existing owner.

Space numbers are staging allowances or provider estimates, not a promise of an
exact download total. Known requirements include headroom on the target
filesystem. Shared Flatpak runtimes and unknown vendor sizes are checked by their
installers. Native Ollama installation checks its binary, library and model
locations separately before downloading. Estimates expire when choices change.

```bash
deckctl setup preview --online
```

## Resume and finish

**Install & finish** shows each selected item, including failed, blocked and
interrupted work. **Resume installation** rechecks completed items before skipping
them. **Retry this item** runs that item and required prerequisites, leaving
unrelated selections alone. Normal UI installs keep stdout and stderr in one
scrollable console. **Details** selects an item's output in that console; **All
steps** returns to the combined view. Turn off **Following latest** to read history
without stopping capture. **Find errors** finds diagnostic keywords with context;
item verification status remains authoritative.

Private bounded latest-attempt item logs are under
`~/.local/state/deckctl/install-logs/`. Each UI run also archives combined output
(including preflight) and item logs under `~/.local/state/deckctl/logs/<run-id>/`.
The console shows the run path. Common token/password patterns are redacted;
review logs before sharing. Explicit interactive vendor/authentication actions
stay in their clearly labeled terminal, with raw sign-in output excluded from
these archives. Logs are not included in portable setup exports.

```bash
deckctl setup install --resume
deckctl setup install --item app:slack
```

Progress survives closing and reopening the app or restarting the Deck. If a
vendor needs interaction, choose **Recheck readiness**, open its setup, finish it,
then resume. Decky Loader must be installed before its plugins can run. CSS
components are processed individually; the final task verifies the complete
palette and recovery profile.

The finish screen separates installed software from sign-in and pairing. Codex
and Claude Code use their own login-status checks. Other account and pairing
steps require your explicit confirmation; those results are labelled as confirmed
by you. App presence alone never proves a working account or connection.

The running item stays at the top with its phase and elapsed time. Managed
terminal downloads show received bytes and a percentage when a server total is
available. Other provider operations show indeterminate progress; a quiet period
is not treated as a failure. Pause/cancel controls remain visible while reading
logs or charts. Network/disk charts include other apps on the Deck, distinguish
stale or unknown measurements, and never treat zero traffic as proof of offline
status. The space meter shows free space against known allowance and reserve;
unknown vendor sizes remain unknown.

## Compare palettes

The CSS Loader page offers color swatches and a live menu/keyboard color study.
The study is explicitly an illustration, not a captured Game Mode screen. The
**Open CSS Loader theme previews** button opens the upstream gallery for real
layout examples. Those examples may use different colors and Steam versions.
Colors apply only to selected components with supported native controls.
Physical Game Mode, controller and touch testing remains a separate acceptance
step on the Deck.

**Theme & appearance** in the sidebar also controls Ghostty, Fastfetch, Oh My
Posh, Starship, Konsole and tmux. Switch off individual targets to preserve their
current colors. No extra tool is installed by a theme switch. Review lists the
selected tools that will receive the palette when installation runs.

Installation shows a completed-item count and brings failures ahead of waiting and
completed items. A successful individual retry does not mark the whole plan
finished while other selections remain incomplete. Appearance choices for tools
that are not selected are labelled as preferences only.
