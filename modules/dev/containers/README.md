# Optional Docker development support

Owned by the existing development module. The normal installer offers this
optional integration after the established workstation/guided setup; declining
is remembered and does not affect other modules. No new top-level module or
change to the existing Podman/Distrobox/Codex path is required.

## Quick start for beacon and RLCS/dashboard projects

```bash
deckctl containers check
deckctl containers install
deckctl containers status
deckctl containers test
cd /path/to/your/dashboard-repository
deckctl containers compose -- config --quiet
deckctl containers compose -- up --build -d
deckctl containers compose -- ps
deckctl containers compose -- logs --tail 100
# Stops this Compose project; omit --volumes to retain named database volumes.
deckctl containers compose -- down
```

Use the project's own Compose file/Dockerfiles. This integration does not include
or certify your beacon or RLCS application's code, credentials or production
configuration. Use test accounts/data. Compose commands run from your current
working directory. Keep `.env` and private service configuration outside this
public workstation repo. Docker arguments are passed as an argv list, not a shell.

For local-only dashboards, explicitly bind published ports to loopback in your
project, for example `"127.0.0.1:8080:8080"`. The wrapper does not rewrite Compose
network settings. Deliberately choose LAN binding when testing beacon traffic
from other machines; do not assume a rootless container's host-network mode is
the physical Deck network. Broadcast, multicast, device access, low ports and
production network topology need separate tests. Avoid port collisions with
Decky/Sunshine and existing services.

## Three engine choices

1. `deckctl containers install` creates a private **rootless** engine only when
   prerequisites pass. If another Docker CLI exists, it asks you to select an
   existing context rather than silently replacing or shadowing it.
2. `deckctl containers install --context default` adopts an existing reachable
   Docker engine and its working Compose plugin. No daemon, credentials or
   default context are changed. A rootful engine may be reused explicitly;
   the project never installs a rootful engine.
3. `deckctl containers install --remote ssh://user@host` installs private CLI,
   Compose and Buildx tools and connects to Docker through SSH. First verify SSH
   authentication/trust with your normal SSH client. The remote account must
   already have Docker access. The installer does not install Docker remotely,
   copy keys, approve SSH host fingerprints, open a TCP Docker socket, or modify
   remote services. Use a Linux Docker host reachable from the Deck, including
   over an already-configured Tailscale connection.

On a remote engine, published ports and bind-mount paths belong to the **remote
machine**. Use an explicit SSH tunnel for local browsing, for example
`ssh -L 8080:127.0.0.1:8080 user@host`, and synchronize bind-mounted source yourself.
Compose builds can send local build contexts, but that does not synchronize a
runtime bind mount. A Windows workstation needs a reachable Linux Docker/SSH
endpoint; WSL2 networking/authentication must be configured separately.

Switch back with `deckctl containers install --local`. Switching the selected
engine does not stop workloads on the previously selected engine.

## Prerequisites and SteamOS

Local managed Docker requires Linux x86_64, a non-root user, a working systemd
user session and XDG_RUNTIME_DIR, `newuidmap`/`newgidmap`, assigned subordinate
UID/GID ranges (at least 65,536), unprivileged user namespaces, `iptables`, and
one supported rootless networking helper. The preflight reports missing items;
`install` returns CONFIG_REQUIRED rather than modifying `/etc`, disabling
security controls, running pacman or unlocking SteamOS. A kernel restriction can
still prevent startup after preflight; inspect `journalctl --user -u
 deckctl-docker.service` (on one line).

The downloaded binaries are pinned in [downloads.json](downloads.json), with
SHA-256 checks. They come from Docker's official binary distribution and
Docker's Compose/Buildx GitHub releases. Compose and Buildx hashes were checked
against their GitHub release asset digests; engine/extras hashes were computed
from the exact official downloads. Downloads have size limits and archives reject
traversal, links, unexpected layouts and duplicate entries. Static binaries do
not receive automatic package-manager security updates: maintainers must review
and update the pins, rerun CI, and test the supported SteamOS builds.

## State, startup and cleanup

- Managed tools, private CLI plugins and engine data:
  `~/.local/share/deckctl/containers/` (normally internal NVMe).
- Selected mode/opt-in state: `~/.config/deckctl/containers.json`, following
  DECKCTL_CONFIG when set. Remote endpoint names are private operational metadata.
- Local user service: `~/.config/systemd/user/deckctl-docker.service`.
- Local socket: `$XDG_RUNTIME_DIR/deckctl-docker.sock`.

No `~/.docker` credentials or existing Docker/Podman services are replaced.
`deckctl containers start` and `stop` affect only the managed local engine.
Stopping it stops its running workloads but retains their data.
`deckctl containers autostart on` opts into startup **at user login**; `off`
disables future automatic starts. Linger/system boot startup is never enabled.

The installer rechecks managed file hashes and reuses intact downloads on retry.
It does not overwrite modified tools/plugins. Temporary download archives are
removed on normal completion/failure. `cleanup` explains this behavior and never
runs Docker prune or removes images, containers, volumes or databases. Keep
persistent project backups separately; the workstation save-backup command does
not claim to back up Docker volumes. Do not remove the engine data directory as
an installer-cleanup operation.

## Verification and limitations

`status` only queries engine/Compose state; it never pulls images or starts a
service. `test` launches [compose-smoke.yaml](compose-smoke.yaml), waits for health,
checks an actual HTTP response, and tears down only its unique test project. It
publishes no ports, mounts no host directory and creates no persistent volume.
The digest-pinned image remains cached for repeat tests. This checks basic Docker
and Compose execution, not your application's behavior or network topology.

CI tests the wrapper against a real Docker engine and builds a small Dockerfile
with Buildx/Compose. Rootless service installation is tested with isolated fake
host commands and resulting-file assertions. Actual Steam Deck rootless startup,
SSH-host behavior, battery impact, and your beacon/RLCS workloads remain hardware
validation items; see the [hardware checklist](../../../docs/HARDWARE-TESTING.md).

Run `deckctl containers --help` and each subcommand's `--help` for full usage,
side effects and exit codes. Exit 0 indicates completion; 1 indicates failure;
2 indicates missing configuration/prerequisites. Vendor command exits propagate.
