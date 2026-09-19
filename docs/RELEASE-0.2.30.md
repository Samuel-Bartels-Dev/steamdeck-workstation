# v0.2.30 — Choose desktop apps and safely remove them

The installer now asks which desktop apps to install: Zen, Zed, VLC, Plex Desktop,
Spotify, VS Code and Flatseal. Saved choices persist across upgrades. Existing
installs keep the previous default of all seven until a choice is saved.

- `deckctl apps select`: interactive chooser; names replace the selection.
- `deckctl apps install`: install the selection, or enable/install named apps.
- `deckctl apps uninstall spotify`: preview; append `--yes` to remove the user app.
- Removal preserves settings and deselects the app to prevent reinstalls.
- Unselected apps no longer fail module verification; Utilities repair respects choices.

Removal is limited to named catalog user Flatpaks. No data purge, runtime prune,
forced removal or system installation changes are performed. Other module features
and vendor setup retain their own controls. See [app management](APPS.md).

Tests cover saved choices, cancellation, corrupt configuration, repeated installs,
partial failures, removal previews, system-only refusal, and recovery after failed
removal. Real installed user apps are retained during validation. The user confirmed
all five apps added in v0.2.29 open successfully; this does not test account login,
playback or editor integrations.
