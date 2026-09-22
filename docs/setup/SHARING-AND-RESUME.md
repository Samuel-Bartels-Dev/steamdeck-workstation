# Share a setup and install only what you need

Choose apps, tools, launchers, Decky plugins and CSS components individually in
`deckctl setup customize`. Dependencies appear as included choices. Deselecting an
item leaves existing software and personal data in place.

## Share choices

Save your plan at Review. **More → Export saved setup** writes a portable ZIP.
It includes module, app, component, launcher, Decky and CSS/palette choices, plus
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

At Review, use **Check downloads & space**. Flatpak commit metadata and managed
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
unrelated selections alone. Detailed provider output stays in Konsole.

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

## Compare palettes

The CSS Loader page offers color swatches and a live menu/keyboard color study.
The study is explicitly an illustration, not a captured Game Mode screen. The
**Open CSS Loader theme previews** button opens the upstream gallery for real
layout examples. Those examples may use different colors and Steam versions.
Colors apply only to selected components with supported native controls.
Physical Game Mode, controller and touch testing remains a separate acceptance
step on the Deck.
