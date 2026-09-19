# v0.2.28 — Desktop apps and tested Docker setup

This release delivers the merged Docker storage repair and shell aliases through
the normal bootstrap, together with guided recovery, clearer status and an
[everyday Docker guide](DOCKER.md).

- Install Zen Browser and Zed editor, plus VLC, Plex Desktop and Spotify, through
  the Utilities, Development and Media modules. These are user Flatpaks from
  Flathub; existing installations are reused. Verification reports missing apps
  and failed downloads can be retried. Sign-in/playback stays inside each app.

- Use `docker ps`, `docker compose up -d`, `docker-compose`, or `compose` in
  Bash/Zsh. Short forms are `d` and `dc`. Setup installs aliases without replacing
  existing commands, functions or personal aliases.
- When the real container test encounters the known rootless overlay mount
  failure, interactive installation offers fuse-overlayfs repair. It explains
  storage visibility, requires the host helper, checks that no containers remain,
  and asks before stopping the managed engine and retrying. Remote/context engines,
  missing helpers, unattended installs and existing containers are not switched.
- `containers status` distinguishes `API_READY` from `READY`. A responding engine
  needs a matching successful launch/HTTP/cleanup test before reporting READY.
  `last_test_at` identifies historical test evidence; failed or interrupted tests
  cannot reuse a prior success. Status remains read-only.
- Test evidence is bound to the selected engine, versions, storage and fixture.
  It does not certify application behavior, network topology or future health.

## Upgrade

Run the normal bootstrap. If Docker setup was previously declined, use
`deckctl containers install` to opt in. To install shell shortcuts independently,
use `deckctl containers aliases`, then open a new terminal or source
`~/.config/deckctl/shell/containers.sh`.

Run `deckctl containers test` after upgrading to create fresh test evidence.
Login startup remains optional through `deckctl containers autostart on`.

## Preservation and recovery

SteamOS system files, other workstation modules, existing credentials and user
data are unchanged by these Docker improvements. Old storage is retained when
switching backends, but its images/containers are hidden by the selected backend;
this is not a migration. No prune or volume deletion is performed. To restore
the default backend, stop the managed engine and use
`deckctl containers install --storage-driver default`; the original overlay
limitation can still apply. Previous control-plane releases remain available.

## Validation scope

Contract coverage includes declined repair, missing prerequisites, noninteractive
setup, existing/concurrently created containers, failed cleanup, interrupted tests,
stale engine evidence and real Bash/Zsh argument forwarding. Release delivery
includes checksum and executable-mode verification in independent tar/USB
extractions. The affected OLED Deck provides live rootless Docker/Compose/Buildx
and HTTP checks. Guided failure branches use isolated simulations; other SteamOS
builds, clean Deck installs and the user's application stacks need their own checks.
