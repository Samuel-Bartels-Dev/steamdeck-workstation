# v0.2.27 — optional Docker and Compose

The public bootstrap installs the latest published release, not the current main
branch. This release delivers the merged Docker support to existing and new Decks.
Rerun the normal bootstrap and answer yes to the optional container setup prompt.
Previously declined setup remains declined; use `deckctl containers install` to opt in.

- User-owned rootless Docker, Compose and Buildx with pinned, SHA-256-verified
  downloads, plus explicit adoption of an existing context or SSH remote endpoint.
- Read-only prerequisite checks and status; start/stop and optional login startup;
  isolated Compose HTTP smoke test with cleanup limited to its own project.
- Manual-style help for every container command, including requirements, paths,
  examples and failure behavior. Run `deckctl containers --help`.
- PR lint gates and real Docker Compose build/HTTP/cleanup integration tests,
  alongside Python 3.12/3.13 regressions and clean archive verification.
- Hardware acceptance checklist, compatibility record, bug-report template and
  MIT licensing for original project code, with separate third-party notices.

After setup, run `deckctl containers status` and `deckctl containers test`.
For an application, enter its project directory and run
`deckctl containers compose -- up -d --build`. The wrapper preserves that directory.

## Preservation and limitations

Existing modules, Android/Google Play provisioning, Decky/CSS selections, desktop
icons, recovery and sanitized support bundles are retained. No Waydroid engine
changes are included. SteamGridDB continues to own Gaming Mode artwork.

Local rootless Docker requires working user namespaces, subordinate UID/GID maps,
UID mapping helpers and the documented host prerequisites. Missing prerequisites
produce CONFIG_REQUIRED; this release does not unlock SteamOS or install system
packages. An existing or remote Docker endpoint can be selected explicitly.
Ubuntu CI proves the Compose workflow; Steam Deck hardware and the user's Beacon
and RLCS application stacks still require acceptance on the target machine.

Original code is MIT-licensed. Upstream theme metadata has separate licensing;
Chromahon-QAM and Controls licensing remains unconfirmed. See
[third-party notices](../THIRD-PARTY-NOTICES.md); the root MIT license does not
relicense those fixtures.
