# Steam Deck Workstation 0.2.44-rc1

This candidate includes the merged palette fixes plus the administrator-dialog
and KeeperFill corrections that were previously merged only into a feature branch.
It uses a new version so installed `deckctl` commands and the setup window load
the same runtime without replacing different files under v0.2.43.

- Managed Docker finds the main user session and socket from Nested Desktop.
- Tailscale detection checks its running/login state and reports DNS warnings.
  Connected installations are reused without another download or login.
- Slow UI status requests run independently of pause/cancel requests; conflicting
  plan-changing actions are serialized.
- New users see a skippable walkthrough automatically. Dismissal is remembered,
  and the guide remains available from the menu. Runtime version appears in setup checks.

This is a release candidate, not a declaration that the full hardware matrix has
passed. Validate clean installation, rerun, cancellation, reboot, and both Desktop
and Gaming Mode before promoting a stable release.
