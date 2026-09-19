# deckctl command manual — v0.2.28

Generated from the runtime help registry. Use `deckctl help COMMAND` or `deckctl COMMAND --help`.

For setup and maintenance entry points, see [Script reference](SCRIPTS.md).

## deckctl

```text
usage: deckctl [-h] [--version]
       {containers,detect,plan,apply,verify,doctor,inventory,support-bundle,post-update,ui,storage,game,remote,backup,restore,travel,ai,repo,profile,launcher,channel,update,export,emulation,media,network,health,terminal,controller,library,aliases,desktop,decky,android,workspace,setup,help}
       ...

NAME
  deckctl  — Operate the Steam Deck workstation.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {containers,detect,plan,apply,verify,doctor,inventory,support-bundle,post-update,ui,storage,game,remote,backup,restore,travel,ai,repo,profile,launcher,channel,update,export,emulation,media,network,health,terminal,controller,library,aliases,desktop,decky,android,workspace,setup,help}
    containers          Manage containers operations.
    detect              Identify Steam Deck model, SteamOS, and battery health from
                        local system files.
    plan                List enabled modules in dependency order with their current
                        readiness.
    apply               Provision enabled modules, recording progress for repeatable
                        retries.
    verify              Run enabled module verifiers and report readiness, including
                        hardware context in JSON mode.
    doctor              Run repair actions for one module, or all enabled modules that
                        are not READY.
    inventory           Report the release version, hardware, module readiness, and
                        storage.
    support-bundle      Create a sanitized diagnostic ZIP from an explicit set of
                        project status and configuration data.
    post-update         Reapply user-space integration after a SteamOS update and
                        inspect essential services.
    ui                  Manage ui operations.
    storage             Manage storage operations.
    game                Manage game operations.
    remote              Manage remote operations.
    backup              Manage backup operations.
    restore             Preview, select, restore and verify categories from a v2
                        save/settings backup.
    travel              Manage travel operations.
    ai                  Manage ai operations.
    repo                Manage repo operations.
    profile             Manage profile operations.
    launcher            Manage launcher operations.
    channel             Show or select the release channel: stable, beta, or dev.
    update              Manage update operations.
    export              Export an inventory of the workstation configuration and
                        registered resources.
    emulation           Manage emulation operations.
    media               Manage media operations.
    network             Manage network operations.
    health              Summarize module, storage, backup, and operational readiness.
    terminal            Manage terminal operations.
    controller          Manage controller operations.
    library             Manage library operations.
    aliases             List convenience shell aliases and the deckctl command each
                        invokes.
    desktop             Manage desktop operations.
    decky               Manage decky operations.
    android             Manage android operations.
    workspace           Manage workspace operations.
    setup               Manage setup operations.
    help                Display the full manual entry for any registered command or
                        command group.

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit

EXAMPLES
  deckctl  containers

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl containers

```text
usage: deckctl containers [-h]
       {status,install,start,stop,test,cleanup,provision,check,aliases,autostart,docker,compose}
       ...

NAME
  deckctl containers — Manage containers operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {status,install,start,stop,test,cleanup,provision,check,aliases,autostart,docker,compose}
    status              Report the selected Docker engine and Compose readiness.
    install             Install optional Docker Engine, Compose and Buildx, or reuse an
                        existing engine.
    start               Start the project-managed local Docker engine for this session.
    stop                Stop the project-managed local Docker engine.
    test                Run and remove a uniquely named Compose HTTP smoke test.
    cleanup             Explain automatic installer cleanup and preserve project data.
    provision           Offer or resume optional Docker setup during the normal
                        installer.
    check               Check host prerequisites for a local rootless Docker engine.
    aliases             Install familiar Docker commands and short shell aliases.
    autostart           Opt in or out of managed Docker startup at user login.
    docker              Run Docker CLI arguments against the selected development
                        engine.
    compose             Run your Compose project against the selected development
                        engine.

options:
  -h, --help            show this help message and exit

EXAMPLES
  deckctl containers status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl containers status

```text
usage: deckctl containers status [-h] [--json]

NAME
  deckctl containers status — Report the selected Docker engine and Compose readiness.

DESCRIPTION
  Read-only: queries the selected engine and Compose, then reads the last test result. API_READY means the API responds but no matching successful launch test exists. READY means the API responds and the last matching launch/HTTP/cleanup test passed; last_test_at shows when, not a live application guarantee. TEST_FAILED or TEST_REQUIRED indicates failed or interrupted testing. Engine, version, storage, endpoint or fixture changes invalidate old evidence. Never starts services, pulls images or writes results. Exit 0 only for READY, otherwise 2. Podman/Distrobox are unchanged.

options:
  -h, --help  show this help message and exit
  --json      Emit machine-readable JSON instead of the human-readable report.

EXAMPLES
  deckctl containers status --json

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl containers install

```text
usage: deckctl containers install [-h] [--storage-driver {default,fuse-overlayfs}]
       [--local | --context CONTEXT | --remote REMOTE]

NAME
  deckctl containers install — Install optional Docker Engine, Compose and Buildx, or reuse an existing engine.

DESCRIPTION
  Opt-in user-space setup. With no flags, checks rootless prerequisites without changing SteamOS, downloads pinned SHA-256-verified tools, creates a separate user service/data directory and starts it for this session. Existing Docker requires --context NAME. --local selects the managed local engine after a remote/context selection. --remote installs private CLI tools for an SSH engine; set up SSH trust/authentication first. Never changes the default Docker context, sudo settings or existing engine. Runs a real Compose smoke test. A known rootless overlay failure offers an interactive fuse-overlayfs repair only when the helper exists and no containers remain. Explains storage visibility and asks before stopping/switching; declining or noninteractive setup returns 2. No automatic binary updates.

options:
  -h, --help            show this help message and exit
  --storage-driver {default,fuse-overlayfs}
                        Select managed rootless storage: Docker default or classic fuse-
                        overlayfs. Stop the engine before switching; old
                        images/containers are preserved but hidden. Saved for retries.
  --local               Explicitly select the managed local rootless engine after using
                        a remote/context engine.
  --context CONTEXT     Reuse an existing Docker context and its Compose plugin without
                        modifying its engine.
  --remote REMOTE       Install private Docker CLI tools targeting
                        ssh://user@hostname[:port]. Authenticate with SSH first.

EXAMPLES
  deckctl containers install

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl containers start

```text
usage: deckctl containers start [-h]

NAME
  deckctl containers start — Start the project-managed local Docker engine for this session.

DESCRIPTION
  Checks prerequisites and starts only deckctl-docker.service. Waits for rootless API/Compose readiness. Does not enable startup or affect another engine.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl containers start

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl containers stop

```text
usage: deckctl containers stop [-h]

NAME
  deckctl containers stop — Stop the project-managed local Docker engine.

DESCRIPTION
  Stops running workloads on this managed engine. Images, containers and volumes remain on disk. Existing/remote engines cannot be stopped through this command.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl containers stop

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl containers test

```text
usage: deckctl containers test [-h]

NAME
  deckctl containers test — Run and remove a uniquely named Compose HTTP smoke test.

DESCRIPTION
  Requires a reachable engine and Compose. May download a digest-pinned BusyBox image, creates a disposable service, waits for health, verifies its HTTP response, and removes only that test project. Records timestamped pass/fail evidence for this engine/storage/fixture; interrupted testing invalidates previous success. Publishes no host ports and uses no volumes. Does not certify your dashboard stack or host networking. Leaves the cached image for reuse.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl containers test

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl containers cleanup

```text
usage: deckctl containers cleanup [-h]

NAME
  deckctl containers cleanup — Explain automatic installer cleanup and preserve project data.

DESCRIPTION
  Downloads are temporary and removed on completion/failure. This read-only command never prunes images, volumes or user containers; database cleanup must be explicit in your project.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl containers cleanup

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl containers provision

```text
usage: deckctl containers provision [-h]

NAME
  deckctl containers provision — Offer or resume optional Docker setup during the normal installer.

DESCRIPTION
  First interactive use asks once; declining records opt-out. Non-interactive setup skips an unselected option. Accepted setup is retried on later installer runs; containers install can opt in after declining. Does not block unrelated modules from provisioning.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl containers provision

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl containers check

```text
usage: deckctl containers check [-h]

NAME
  deckctl containers check — Check host prerequisites for a local rootless Docker engine.

DESCRIPTION
  Read-only host checks for Linux x86_64, UID/GID mapping, subordinate ranges, network helper, user namespaces and a systemd user session. No sudo, pacman, sysctl edits or SteamOS unlock. Missing prerequisites return 2; remote Docker may still be usable.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl containers check

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl containers aliases

```text
usage: deckctl containers aliases [-h]

NAME
  deckctl containers aliases — Install familiar Docker commands and short shell aliases.

DESCRIPTION
  Installs docker, docker-compose, compose, d (Docker), and dc (Compose) for Bash and Zsh after Docker is configured. Open a new terminal or source ~/.config/deckctl/shell/containers.sh. Existing executables, functions and aliases take precedence. Arguments and the working directory pass through unchanged; all Docker subcommands including buildx use the selected engine. These are interactive shell aliases, not executables for scripts or sudo. Scripts can use deckctl containers docker/compose --. Does not start the engine or run containers.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl containers aliases

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl containers autostart

```text
usage: deckctl containers autostart [-h] {on,off}

NAME
  deckctl containers autostart — Opt in or out of managed Docker startup at user login.

DESCRIPTION
  on enables the managed user service; off disables future automatic starts without stopping current workloads. Does not enable linger or boot startup. The default is off.

positional arguments:
  {on,off}    Enable or disable managed Docker startup at user login; no system
              boot/linger changes.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl containers autostart on

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl containers docker

```text
usage: deckctl containers docker [-h] ...

NAME
  deckctl containers docker — Run Docker CLI arguments against the selected development engine.

DESCRIPTION
  Pass arguments after --. Normal Docker semantics apply, including destructive operations you explicitly request. Endpoint overrides are rejected. Private tools do not replace the system docker command. Remote bind mounts refer to the remote host.

positional arguments:
  arguments   Arguments passed to the selected Docker/Compose endpoint; use -- before
              vendor options.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl containers docker -- ps

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl containers compose

```text
usage: deckctl containers compose [-h] ...

NAME
  deckctl containers compose — Run your Compose project against the selected development engine.

DESCRIPTION
  Runs in your current working directory. Pass Compose arguments after --; vendor operations can build images, start services or delete data as requested. No automatic port rewriting: bind local dashboards to 127.0.0.1 explicitly. On SSH engines bind mounts and published ports belong to the remote host.

positional arguments:
  arguments   Arguments passed to the selected Docker/Compose endpoint; use -- before
              vendor options.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl containers compose -- up --build -d

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl detect

```text
usage: deckctl detect [-h]

NAME
  deckctl detect — Identify Steam Deck model, SteamOS, and battery health from local system files.

DESCRIPTION
  Read-only. Unknown hardware remains unknown; no model is guessed.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl detect

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl plan

```text
usage: deckctl plan [-h]

NAME
  deckctl plan — List enabled modules in dependency order with their current readiness.

DESCRIPTION
  Read-only. Runs module verifiers; does not provision anything.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl plan

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl apply

```text
usage: deckctl apply [-h]

NAME
  deckctl apply — Provision enabled modules, recording progress for repeatable retries.

DESCRIPTION
  Within the same release, skips previously ready modules only if a fresh verifier still confirms readiness. New releases rerun module reconciliation. Records interruptions before execution and failures after execution; continues other modules. Account/vendor configuration may require setup run.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl apply

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl verify

```text
usage: deckctl verify [-h] [--json]

NAME
  deckctl verify — Run enabled module verifiers and report readiness, including hardware context in JSON mode.

DESCRIPTION
  Read-only. Exit 0: ready/optional; 1: failed or absent; 2: degraded or user configuration required. A verifier timeout is FAILED.

options:
  -h, --help  show this help message and exit
  --json      Emit machine-readable JSON instead of the human-readable report.

EXAMPLES
  deckctl verify --json

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl doctor

```text
usage: deckctl doctor [-h] [module]

NAME
  deckctl doctor — Run repair actions for one module, or all enabled modules that are not READY.

DESCRIPTION
  May install packages, rewrite managed configuration, or launch vendor repair. Rechecks readiness afterward using the same exit statuses as verify.

positional arguments:
  module      Registered module ID, such as decky or terminal; omit where allowed to
              cover enabled modules.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl doctor decky

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl inventory

```text
usage: deckctl inventory [-h] [--json]

NAME
  deckctl inventory — Report the release version, hardware, module readiness, and storage.

DESCRIPTION
  Read-only. Output may contain private host addresses and paths; use support-bundle for sharing.

options:
  -h, --help  show this help message and exit
  --json      Emit machine-readable JSON instead of the human-readable report.

EXAMPLES
  deckctl inventory --json

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl support-bundle

```text
usage: deckctl support-bundle [-h]

NAME
  deckctl support-bundle — Create a sanitized diagnostic ZIP from an explicit set of project status and configuration data.

DESCRIPTION
  Writes ~/DeckSupportBundles. Excludes credential stores, keys, passwords, ROMs, BIOS, saves, and arbitrary logs/files. Inspect before sharing.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl support-bundle

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl post-update

```text
usage: deckctl post-update [-h]

NAME
  deckctl post-update — Reapply user-space integration after a SteamOS update and inspect essential services.

DESCRIPTION
  Restages Decky setup and repairs terminal configuration, selected Decky plugins/CSS, and controller templates. Vendor authentication may remain required.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl post-update

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl ui

```text
usage: deckctl ui [-h] {safe,restore} ...

NAME
  deckctl ui — Manage ui operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {safe,restore}
    safe          Capture CSS profiles and enter a recoverable UI safe mode.
    restore       Restore UI state captured by ui safe.

options:
  -h, --help      show this help message and exit

EXAMPLES
  deckctl ui safe

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl ui safe

```text
usage: deckctl ui safe [-h] [--minimal]

NAME
  deckctl ui safe — Capture CSS profiles and enter a recoverable UI safe mode.

DESCRIPTION
  Moves active CSS profiles out of service and records restoration state. --minimal also stops Decky’s plugin service; may request sudo.

options:
  -h, --help  show this help message and exit
  --minimal   Also stop the Decky plugin service while entering safe mode.

EXAMPLES
  deckctl ui safe --minimal

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl ui restore

```text
usage: deckctl ui restore [-h]

NAME
  deckctl ui restore — Restore UI state captured by ui safe.

DESCRIPTION
  Restores saved profile locations and restarts the plugin service when needed. No-op guidance is printed when no safe-mode snapshot exists.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl ui restore

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl storage

```text
usage: deckctl storage [-h]
       {health,recommend,migration-status,verify-migration,migrate-emulation,finalize-emulation-migration}
       ...

NAME
  deckctl storage — Manage storage operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {health,recommend,migration-status,verify-migration,migrate-emulation,finalize-emulation-migration}
    health              Inspect block devices, mount points, free space, and configured
                        storage roles.
    recommend           Recommend a storage role using game hints or an explicit
                        emulation system.
    migration-status    Inspect internal and removable Emulation directory locations and
                        migration prerequisites.
    verify-migration    Compare preserved Emulation content with the mounted DECK-EMU
                        destination.
    migrate-emulation   Stage a migration guide and launch EmuDeck’s supported migration
                        workflow.
    finalize-emulation-migration
                        Verify migrated content and switch the internal Emulation path
                        to the card.

options:
  -h, --help            show this help message and exit

EXAMPLES
  deckctl storage health

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl storage health

```text
usage: deckctl storage health [-h] [--json]

NAME
  deckctl storage health — Inspect block devices, mount points, free space, and configured storage roles.

DESCRIPTION
  Read-only. Uses lsblk; does not format, mount, or move data.

options:
  -h, --help  show this help message and exit
  --json      Emit machine-readable JSON instead of the human-readable report.

EXAMPLES
  deckctl storage health --json

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl storage recommend

```text
usage: deckctl storage recommend [-h] [--system SYSTEM] game

NAME
  deckctl storage recommend — Recommend a storage role using game hints or an explicit emulation system.

DESCRIPTION
  Read-only advice. No game files are moved.

positional arguments:
  game             Game title to evaluate; quote spaces.

options:
  -h, --help       show this help message and exit
  --system SYSTEM  Emulation system identifier used to tailor the recommendation.

EXAMPLES
  deckctl storage recommend "World of Warcraft"

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl storage migration-status

```text
usage: deckctl storage migration-status [-h]

NAME
  deckctl storage migration-status — Inspect internal and removable Emulation directory locations and migration prerequisites.

DESCRIPTION
  Read-only. Use this before migrating or finalizing a migration.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl storage migration-status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl storage verify-migration

```text
usage: deckctl storage verify-migration [-h] [--json]

NAME
  deckctl storage verify-migration — Compare preserved Emulation content with the mounted DECK-EMU destination.

DESCRIPTION
  Read-only SHA-256 comparison of all source files and directory entries, including saves, BIOS and ROMs. Extra destination files are retained. Missing cards, symlinks needing review and mismatched files return 2; --json emits results. Close emulators before verification/finalization.

options:
  -h, --help  show this help message and exit
  --json      Emit machine-readable JSON instead of the human-readable report.

EXAMPLES
  deckctl storage verify-migration --json

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl storage migrate-emulation

```text
usage: deckctl storage migrate-emulation [-h]

NAME
  deckctl storage migrate-emulation — Stage a migration guide and launch EmuDeck’s supported migration workflow.

DESCRIPTION
  Records migration intent and opens EmuDeck when available. EmuDeck performs the migration; the original tree must be retained until you verify games and saves.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl storage migrate-emulation

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl storage finalize-emulation-migration

```text
usage: deckctl storage finalize-emulation-migration [-h] [--yes]

NAME
  deckctl storage finalize-emulation-migration — Verify migrated content and switch the internal Emulation path to the card.

DESCRIPTION
  Compares every preserved source entry with SHA-256 before changing paths. --yes renames the original to a rollback directory and creates an Emulation symlink to the verified card. Never deletes original data. Existing correct vendor migration links remain unchanged; mismatched links fail. Close emulators first.

options:
  -h, --help  show this help message and exit
  --yes       Accept this command’s confirmation prompts; prerequisite checks still run.

EXAMPLES
  deckctl storage finalize-emulation-migration --yes

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl game

```text
usage: deckctl game [-h] {register,ready,doctor} ...

NAME
  deckctl game — Manage game operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {register,ready,doctor}
    register            Record a locally installed game, its launcher, location, and
                        storage role.
    ready               Check a registered game’s location and readiness requirements.
    doctor              Explain readiness problems for a registered game with additional
                        diagnostics.

options:
  -h, --help            show this help message and exit

EXAMPLES
  deckctl game register

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl game register

```text
usage: deckctl game register [-h] --launcher LAUNCHER --path PATH --storage-role
       {internal,pc_games,emulation} name

NAME
  deckctl game register — Record a locally installed game, its launcher, location, and storage role.

DESCRIPTION
  Updates the game registry; does not download or install the game. Quote names and paths containing spaces.

positional arguments:
  name                  Name of the registered object, bundled profile, or capture; see
                        DESCRIPTION and EXAMPLES.

options:
  -h, --help            show this help message and exit
  --launcher LAUNCHER   Launcher identifier to record for this game.
  --path PATH           Existing game installation path; quote spaces.
  --storage-role {internal,pc_games,emulation}
                        Storage role associated with the registered game.

EXAMPLES
  deckctl game register "Example Game" --launcher steam --path ~/Games/example --storage-role internal

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl game ready

```text
usage: deckctl game ready [-h] name

NAME
  deckctl game ready — Check a registered game’s location and readiness requirements.

DESCRIPTION
  Read-only. Returns a nonzero status when requirements are missing.

positional arguments:
  name        Name of the registered object, bundled profile, or capture; see
              DESCRIPTION and EXAMPLES.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl game ready "Example Game"

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl game doctor

```text
usage: deckctl game doctor [-h] name

NAME
  deckctl game doctor — Explain readiness problems for a registered game with additional diagnostics.

DESCRIPTION
  Inspects the registered path and launcher information; follow the reported corrective guidance.

positional arguments:
  name        Name of the registered object, bundled profile, or capture; see
              DESCRIPTION and EXAMPLES.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl game doctor "Example Game"

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl remote

```text
usage: deckctl remote [-h] {register,test,wake,wait,host-kit} ...

NAME
  deckctl remote — Manage remote operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {register,test,wake,wait,host-kit}
    register            Register a Sunshine host reachable by hostname, IP, or Tailscale
                        address.
    test                Probe a registered host’s Sunshine TCP port and available
                        Tailscale connectivity.
    wake                Send a Wake-on-LAN magic packet directly or through the
                        configured SSH relay.
    wait                Poll a registered Sunshine host until its port is reachable or
                        the timeout expires.
    host-kit            Package the Windows Sunshine host setup scripts and selected
                        registered host metadata.

options:
  -h, --help            show this help message and exit

EXAMPLES
  deckctl remote register

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl remote register

```text
usage: deckctl remote register [-h] --target TARGET [--mac MAC] [--relay RELAY]
       [--sunshine-port SUNSHINE_PORT] name

NAME
  deckctl remote register — Register a Sunshine host reachable by hostname, IP, or Tailscale address.

DESCRIPTION
  Writes hosts.json. Optional MAC enables Wake-on-LAN; relay is an SSH user@host on the host’s local network. Port must be 1..65535.

positional arguments:
  name                  Name of the registered object, bundled profile, or capture; see
                        DESCRIPTION and EXAMPLES.

options:
  -h, --help            show this help message and exit
  --target TARGET       Host address for registration, or game/application title for
                        controller advice.
  --mac MAC             Wake-on-LAN MAC address in six-byte colon-separated form.
  --relay RELAY         SSH destination (user@hostname) on the remote host’s local
                        network.
  --sunshine-port SUNSHINE_PORT
                        Sunshine TCP probe port (default: 47984; range: 1..65535).

EXAMPLES
  deckctl remote register desktop --target desktop --mac AA:BB:CC:DD:EE:FF

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl remote test

```text
usage: deckctl remote test [-h] name

NAME
  deckctl remote test — Probe a registered host’s Sunshine TCP port and available Tailscale connectivity.

DESCRIPTION
  Network diagnostics only. A TCP response does not prove pairing or successful video streaming; inspect each result.

positional arguments:
  name        Name of the registered object, bundled profile, or capture; see
              DESCRIPTION and EXAMPLES.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl remote test desktop

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl remote wake

```text
usage: deckctl remote wake [-h] name

NAME
  deckctl remote wake — Send a Wake-on-LAN magic packet directly or through the configured SSH relay.

DESCRIPTION
  Sends a broadcast packet. Requires a registered MAC and host firmware/NIC support; sending the packet does not prove the host woke.

positional arguments:
  name        Name of the registered object, bundled profile, or capture; see
              DESCRIPTION and EXAMPLES.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl remote wake desktop

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl remote wait

```text
usage: deckctl remote wait [-h] [--timeout TIMEOUT] name

NAME
  deckctl remote wait — Poll a registered Sunshine host until its port is reachable or the timeout expires.

DESCRIPTION
  Network probes only. Returns 0 on reachability and nonzero on timeout. Does not launch a stream.

positional arguments:
  name               Name of the registered object, bundled profile, or capture; see
                     DESCRIPTION and EXAMPLES.

options:
  -h, --help         show this help message and exit
  --timeout TIMEOUT  Maximum number of seconds to wait for host reachability (default:
                     90).

EXAMPLES
  deckctl remote wait desktop --timeout 90

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl remote host-kit

```text
usage: deckctl remote host-kit [-h] [--out OUT] name

NAME
  deckctl remote host-kit — Package the Windows Sunshine host setup scripts and selected registered host metadata.

DESCRIPTION
  Writes a ZIP in ~/DeckExports or --out. Does not execute Windows code on the Deck. Host names must be safe filename components.

positional arguments:
  name        Name of the registered object, bundled profile, or capture; see
              DESCRIPTION and EXAMPLES.

options:
  -h, --help  show this help message and exit
  --out OUT   Output file for profile export; output directory for remote host-kit.

EXAMPLES
  deckctl remote host-kit desktop --out ~/DeckExports

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl backup

```text
usage: deckctl backup [-h] {saves} ...

NAME
  deckctl backup — Manage backup operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {saves}
    saves     Archive discovered emulator saves, WoW configuration, and project
              configuration with a restore manifest.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl backup saves

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl backup saves

```text
usage: deckctl backup saves [-h]

NAME
  deckctl backup saves — Archive discovered emulator saves, WoW configuration, and project configuration with a restore manifest.

DESCRIPTION
  Writes the configured backup destination. Contains private saves/configuration: keep it private and verify the manifest. It is not a sanitized support bundle.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl backup saves

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl restore

```text
usage: deckctl restore [-h] [--dry-run] [--category CATEGORY] [--yes] [archive]

NAME
  deckctl restore — Preview, select, restore and verify categories from a v2 save/settings backup.

DESCRIPTION
  --dry-run validates paths, categories and free space without restoring. --category NAME is repeatable; --yes accepts selection without a dialog. Previous content is retained under state/restore-rollback; writes are atomic per file and SHA-256 checked afterward. A failed run retains its rollback and journal. This restores personal data, not app binaries or login sessions; run apply/setup afterward as needed.

positional arguments:
  archive              Path to a trusted archive. Restore can prompt when omitted;
                       update can download from the configured release source.

options:
  -h, --help           show this help message and exit
  --dry-run            Show intended Decky plugin operations without installing them.
  --category CATEGORY  Restore only this category; repeat to select several.
  --yes                Accept this command’s confirmation prompts; prerequisite checks
                       still run.

EXAMPLES
  deckctl restore ~/DeckBackups/backup.tar.gz --dry-run

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl travel

```text
usage: deckctl travel [-h] {check,lock,unlock} ...

NAME
  deckctl travel — Manage travel operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {check,lock,unlock}
    check              Check readiness for offline travel, including module readiness
                       and reminders about backup and remote checks.
    lock               Enable the project travel-mode setting.
    unlock             Disable the project travel-mode setting.

options:
  -h, --help           show this help message and exit

EXAMPLES
  deckctl travel check

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl travel check

```text
usage: deckctl travel check [-h]

NAME
  deckctl travel check — Check readiness for offline travel, including module readiness and reminders about backup and remote checks.

DESCRIPTION
  Read-only. A passing check cannot validate every game’s offline license; launch your games offline before leaving.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl travel check

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl travel lock

```text
usage: deckctl travel lock [-h]

NAME
  deckctl travel lock — Enable the project travel-mode setting.

DESCRIPTION
  Writes a travel-lock record. This does not switch off radios or guarantee offline game licensing.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl travel lock

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl travel unlock

```text
usage: deckctl travel unlock [-h]

NAME
  deckctl travel unlock — Disable the project travel-mode setting.

DESCRIPTION
  Removes the travel-lock record. This does not change network interfaces.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl travel unlock

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl ai

```text
usage: deckctl ai [-h] {context,task} ...

NAME
  deckctl ai — Manage ai operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {context,task}
    context       Print the engineering context and module documentation used for an AI-
                  assisted task.
    task          Create a local task document for a module and supplied description.

options:
  -h, --help      show this help message and exit

EXAMPLES
  deckctl ai context

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl ai context

```text
usage: deckctl ai context [-h] module

NAME
  deckctl ai context — Print the engineering context and module documentation used for an AI-assisted task.

DESCRIPTION
  Read-only. MODULE must identify a registered module.

positional arguments:
  module      Registered module ID, such as decky or terminal; omit where allowed to
              cover enabled modules.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl ai context decky

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl ai task

```text
usage: deckctl ai task [-h] module description

NAME
  deckctl ai task — Create a local task document for a module and supplied description.

DESCRIPTION
  Writes a task file in tasks/active in the repository. Does not contact an AI service or send project data.

positional arguments:
  module       Registered module ID, such as decky or terminal; omit where allowed to
               cover enabled modules.
  description  Task description; quote as one argument when it contains spaces.

options:
  -h, --help   show this help message and exit

EXAMPLES
  deckctl ai task decky "Inspect plugin readiness"

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl repo

```text
usage: deckctl repo [-h] {validate} ...

NAME
  deckctl repo — Manage repo operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {validate}
    validate  Run repository contracts, syntax checks, feature guards, and behavioral
              regression tests.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl repo validate

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl repo validate

```text
usage: deckctl repo validate [-h]

NAME
  deckctl repo validate — Run repository contracts, syntax checks, feature guards, and behavioral regression tests.

DESCRIPTION
  Runs offline tests in isolated temporary homes. Python compilation may create build caches. Returns nonzero for any failing gate; does not install vendor applications.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl repo validate

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl profile

```text
usage: deckctl profile [-h] {list,show,apply,auto,export,import} ...

NAME
  deckctl profile — Manage profile operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {list,show,apply,auto,export,import}
    list                List bundled hardware/behavior profiles.
    show                Display the requested bundled deckctl profile.
    apply               Select a bundled deckctl hardware/behavior profile.
    auto                Select the bundled profile matching detected Deck hardware.
    export              Package portable desired state, captured CSS profiles, and
                        controller layouts.
    import              Validate and import a portable desired-state ZIP.

options:
  -h, --help            show this help message and exit

EXAMPLES
  deckctl profile list

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl profile list

```text
usage: deckctl profile list [-h]

NAME
  deckctl profile list — List bundled hardware/behavior profiles.

DESCRIPTION
  Read-only. These are deckctl profiles, separate from CSS Loader profiles.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl profile list

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl profile show

```text
usage: deckctl profile show [-h] name

NAME
  deckctl profile show — Display the requested bundled deckctl profile.

DESCRIPTION
  Read-only. Prints the profile’s configuration so it can be reviewed before applying.

positional arguments:
  name        Name of the registered object, bundled profile, or capture; see
              DESCRIPTION and EXAMPLES.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl profile show oled

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl profile apply

```text
usage: deckctl profile apply [-h] name

NAME
  deckctl profile apply — Select a bundled deckctl hardware/behavior profile.

DESCRIPTION
  Writes the active profile setting. Does not independently reinstall all modules.

positional arguments:
  name        Name of the registered object, bundled profile, or capture; see
              DESCRIPTION and EXAMPLES.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl profile apply oled

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl profile auto

```text
usage: deckctl profile auto [-h]

NAME
  deckctl profile auto — Select the bundled profile matching detected Deck hardware.

DESCRIPTION
  Writes the profile selection when hardware can be identified; unknown hardware needs an explicit selection.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl profile auto

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl profile export

```text
usage: deckctl profile export [-h] [--out OUT]

NAME
  deckctl profile export — Package portable desired state, captured CSS profiles, and controller layouts.

DESCRIPTION
  Writes a sanitized profile ZIP; captures live CSS profiles first. Only approved configuration formats are exported. Browser/Keeper credentials and arbitrary folders are excluded.

options:
  -h, --help  show this help message and exit
  --out OUT   Output file for profile export; output directory for remote host-kit.

EXAMPLES
  deckctl profile export --out ~/DeckExports/my-profile.zip

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl profile import

```text
usage: deckctl profile import [-h] archive

NAME
  deckctl profile import — Validate and import a portable desired-state ZIP.

DESCRIPTION
  Copies approved configuration files after preflight and saves previous files under state/profile-import-rollback. Apply the reported component commands afterward; import does not run bundled scripts.

positional arguments:
  archive     Path to a trusted archive. Restore can prompt when omitted; update can
              download from the configured release source.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl profile import ~/DeckExports/my-profile.zip

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl launcher

```text
usage: deckctl launcher [-h] {status,install} ...

NAME
  deckctl launcher — Manage launcher operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {status,install}
    status          Inspect launcher prerequisites and known game-launcher
                    installations.
    install         Launch the established Battle.net installation workflow.

options:
  -h, --help        show this help message and exit

EXAMPLES
  deckctl launcher status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl launcher status

```text
usage: deckctl launcher status [-h]

NAME
  deckctl launcher status — Inspect launcher prerequisites and known game-launcher installations.

DESCRIPTION
  Read-only. Installed launchers may still need an account login.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl launcher status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl launcher install

```text
usage: deckctl launcher install [-h] {battlenet}

NAME
  deckctl launcher install — Launch the established Battle.net installation workflow.

DESCRIPTION
  Installs/configures the Battle.net launcher through the project’s existing user-space path. Blizzard login, game ownership, and downloads require user interaction.

positional arguments:
  {battlenet}  Name of the registered object, bundled profile, or capture; see
               DESCRIPTION and EXAMPLES.

options:
  -h, --help   show this help message and exit

EXAMPLES
  deckctl launcher install battlenet

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl channel

```text
usage: deckctl channel [-h] [name]

NAME
  deckctl channel — Show or select the release channel: stable, beta, or dev.

DESCRIPTION
  Without NAME, read-only. With NAME, saves the selection for future update checks; does not install a release.

positional arguments:
  name        Name of the registered object, bundled profile, or capture; see
              DESCRIPTION and EXAMPLES.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl channel stable

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl update

```text
usage: deckctl update [-h] {check,apply,rollback,preview} ...

NAME
  deckctl update — Manage update operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation. With no subcommand, update runs update check.

positional arguments:
  {check,apply,rollback,preview}
    check               Query the configured release source and display the installed
                        and available versions.
    apply               Validate and install a new persistent control-plane release.
    rollback            Select an available previous persistent release and reactivate
                        its control plane.
    preview             Compare a candidate release with the currently installed control
                        plane.

options:
  -h, --help            show this help message and exit

EXAMPLES
  deckctl update check

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl update check

```text
usage: deckctl update check [-h]

NAME
  deckctl update check — Query the configured release source and display the installed and available versions.

DESCRIPTION
  Read-only except network access. With no configured source, explains how to use a local archive.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl update check

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl update apply

```text
usage: deckctl update apply [-h] [--archive ARCHIVE]

NAME
  deckctl update apply — Validate and install a new persistent control-plane release.

DESCRIPTION
  Uses --archive locally or downloads a release with checksum verification. Runs repository tests before installation and records rollback history. Removes its own unchanged downloaded tarball after successful promotion; keeps explicitly supplied archives and prior releases. Local archives must be trusted executable code.

options:
  -h, --help         show this help message and exit
  --archive ARCHIVE  Path to a trusted archive. Restore can prompt when omitted; update
                     can download from the configured release source.

EXAMPLES
  deckctl update apply --archive ~/Downloads/steamdeck-workstation-v0.2.28.tar.gz

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl update rollback

```text
usage: deckctl update rollback [-h]

NAME
  deckctl update rollback — Select an available previous persistent release and reactivate its control plane.

DESCRIPTION
  Changes the current-release link and records history. Does not roll back user data, vendor packages, or external service changes.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl update rollback

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl update preview

```text
usage: deckctl update preview [-h] (--archive ARCHIVE | --source SOURCE) [--json]

NAME
  deckctl update preview — Compare a candidate release with the currently installed control plane.

DESCRIPTION
  Read-only except temporary archive extraction. Requires --archive FILE or --source DIRECTORY. Lists added/changed/removed release files, pending Decky additions and preserved user state. Does not execute candidate code, download plugins or promote releases.

options:
  -h, --help         show this help message and exit
  --archive ARCHIVE  Path to a trusted archive. Restore can prompt when omitted; update
                     can download from the configured release source.
  --source SOURCE    Existing local source file or directory; see DESCRIPTION for the
                     required format.
  --json             Emit machine-readable JSON instead of the human-readable report.

EXAMPLES
  deckctl update preview --archive ~/Downloads/steamdeck-workstation-v0.2.28.tar.gz

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl export

```text
usage: deckctl export [-h]

NAME
  deckctl export — Export an inventory of the workstation configuration and registered resources.

DESCRIPTION
  Writes ~/DeckExports. This private inventory can include host addresses and personal paths; use support-bundle for sanitized diagnostics.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl export

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl emulation

```text
usage: deckctl emulation [-h] {bios-audit,bios-import} ...

NAME
  deckctl emulation — Manage emulation operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {bios-audit,bios-import}
    bios-audit          Inspect expected BIOS locations and optionally an import source
                        without copying firmware.
    bios-import         Copy BIOS files from a user-provided directory into the
                        established emulator BIOS location.

options:
  -h, --help            show this help message and exit

EXAMPLES
  deckctl emulation bios-audit

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl emulation bios-audit

```text
usage: deckctl emulation bios-audit [-h] [--source SOURCE]

NAME
  deckctl emulation bios-audit — Inspect expected BIOS locations and optionally an import source without copying firmware.

DESCRIPTION
  Read-only. Supply your own legally obtained files; the project ships no BIOS payloads.

options:
  -h, --help       show this help message and exit
  --source SOURCE  Existing local source file or directory; see DESCRIPTION for the
                   required format.

EXAMPLES
  deckctl emulation bios-audit --source ~/BIOS

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl emulation bios-import

```text
usage: deckctl emulation bios-import [-h] --source SOURCE

NAME
  deckctl emulation bios-import — Copy BIOS files from a user-provided directory into the established emulator BIOS location.

DESCRIPTION
  Copies local firmware files. Does not download BIOS or ROMs; ensure the configured emulation destination is mounted.

options:
  -h, --help       show this help message and exit
  --source SOURCE  Existing local source file or directory; see DESCRIPTION for the
                   required format.

EXAMPLES
  deckctl emulation bios-import --source ~/BIOS

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl media

```text
usage: deckctl media [-h] {setup,status,keeper} ...

NAME
  deckctl media — Manage media operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {setup,status,keeper}
    setup               Create browser-backed media applications, launchers, and Desktop
                        shortcuts.
    status              Inspect media application files and shortcut integration.
    keeper              Manage media keeper operations.

options:
  -h, --help            show this help message and exit

EXAMPLES
  deckctl media setup

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl media setup

```text
usage: deckctl media setup [-h]

NAME
  deckctl media setup — Create browser-backed media applications, launchers, and Desktop shortcuts.

DESCRIPTION
  Installs/configures the browser integration and intentional Desktop icons. Services still require your login; SteamGridDB owns Gaming Mode artwork.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl media setup

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl media status

```text
usage: deckctl media status [-h]

NAME
  deckctl media status — Inspect media application files and shortcut integration.

DESCRIPTION
  Read-only. Presence does not verify subscriptions, login sessions, or DRM playback.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl media status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl media keeper

```text
usage: deckctl media keeper [-h] {setup,status} ...

NAME
  deckctl media keeper — Manage media keeper operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {setup,status}
    setup         Install or open the Keeper password-manager integration.
    status        Check whether Keeper integration is available.

options:
  -h, --help      show this help message and exit

EXAMPLES
  deckctl media keeper setup

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl media keeper setup

```text
usage: deckctl media keeper setup [-h]

NAME
  deckctl media keeper setup — Install or open the Keeper password-manager integration.

DESCRIPTION
  May install the application and open account setup. Passwords and vault contents are never collected by support-bundle.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl media keeper setup

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl media keeper status

```text
usage: deckctl media keeper status [-h]

NAME
  deckctl media keeper status — Check whether Keeper integration is available.

DESCRIPTION
  Read-only. Does not inspect vault contents or verify credentials.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl media keeper status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl network

```text
usage: deckctl network [-h] {test} ...

NAME
  deckctl network — Manage network operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {test}
    test      Report network diagnostics and optionally test a registered streaming
              host.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl network test

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl network test

```text
usage: deckctl network test [-h] [--host HOST] [--json]

NAME
  deckctl network test — Report network diagnostics and optionally test a registered streaming host.

DESCRIPTION
  Performs network probes and reads local connectivity information. Inspect individual results; diagnostic output may include network addresses.

options:
  -h, --help   show this help message and exit
  --host HOST  Name of a previously registered Sunshine host.
  --json       Emit machine-readable JSON instead of the human-readable report.

EXAMPLES
  deckctl network test --host desktop --json

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl health

```text
usage: deckctl health [-h] [--json]

NAME
  deckctl health — Summarize module, storage, backup, and operational readiness.

DESCRIPTION
  Read-only summary. Inspect individual readiness states; use verify for an aggregate automation exit status.

options:
  -h, --help  show this help message and exit
  --json      Emit machine-readable JSON instead of the human-readable report.

EXAMPLES
  deckctl health --json

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl terminal

```text
usage: deckctl terminal [-h] {status,apply,reset,font-check,prompt,tmux} ...

NAME
  deckctl terminal — Manage terminal operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {status,apply,reset,font-check,prompt,tmux}
    status              Inspect installed terminal tools, prompt selection, shell
                        integration, and tmux configuration.
    apply               Install the user-space terminal stack and apply managed shell,
                        prompt, font, and tmux configuration.
    reset               Remove managed terminal integration and eligible managed tool
                        files.
    font-check          Check the configured Nerd Font using local font discovery.
    prompt              Manage terminal prompt operations.
    tmux                Manage terminal tmux operations.

options:
  -h, --help            show this help message and exit

EXAMPLES
  deckctl terminal status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl terminal status

```text
usage: deckctl terminal status [-h] [--json]

NAME
  deckctl terminal status — Inspect installed terminal tools, prompt selection, shell integration, and tmux configuration.

DESCRIPTION
  Read-only. Returns nonzero if the managed terminal stack is incomplete.

options:
  -h, --help  show this help message and exit
  --json      Emit machine-readable JSON instead of the human-readable report.

EXAMPLES
  deckctl terminal status --json

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl terminal apply

```text
usage: deckctl terminal apply [-h] [--config-only] [--refresh]

NAME
  deckctl terminal apply — Install the user-space terminal stack and apply managed shell, prompt, font, and tmux configuration.

DESCRIPTION
  May download tools and fonts and update managed configuration. --config-only avoids tool downloads; --refresh rechecks/downloads upstream assets.

options:
  -h, --help     show this help message and exit
  --config-only  Apply managed configuration without downloading terminal tools.
  --refresh      Refresh upstream terminal tool assets instead of relying on the
                 existing installation.

EXAMPLES
  deckctl terminal apply --config-only

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl terminal reset

```text
usage: deckctl terminal reset [-h] [--keep-tools]

NAME
  deckctl terminal reset — Remove managed terminal integration and eligible managed tool files.

DESCRIPTION
  Uses installation receipts to preserve modified or unmanaged files. --keep-tools retains installed binaries/fonts. Review status before resetting.

options:
  -h, --help    show this help message and exit
  --keep-tools  Retain managed tool binaries/fonts while removing terminal integration.

EXAMPLES
  deckctl terminal reset --keep-tools

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl terminal font-check

```text
usage: deckctl terminal font-check [-h]

NAME
  deckctl terminal font-check — Check the configured Nerd Font using local font discovery.

DESCRIPTION
  Read-only. A missing font can cause prompt glyphs to render incorrectly.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl terminal font-check

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl terminal prompt

```text
usage: deckctl terminal prompt [-h] {status,use} ...

NAME
  deckctl terminal prompt — Manage terminal prompt operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {status,use}
    status      Show the selected prompt engine and managed prompt configuration.
    use         Choose Oh My Posh (posh) or Starship for managed shells.

options:
  -h, --help    show this help message and exit

EXAMPLES
  deckctl terminal prompt status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl terminal prompt status

```text
usage: deckctl terminal prompt status [-h]

NAME
  deckctl terminal prompt status — Show the selected prompt engine and managed prompt configuration.

DESCRIPTION
  Read-only. Supports Oh My Posh and Starship.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl terminal prompt status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl terminal prompt use

```text
usage: deckctl terminal prompt use [-h] {posh,starship}

NAME
  deckctl terminal prompt use — Choose Oh My Posh (posh) or Starship for managed shells.

DESCRIPTION
  Updates prompt selection and shell integration. Open a new shell to see the result.

positional arguments:
  {posh,starship}  Prompt engine: posh (Oh My Posh) or starship.

options:
  -h, --help       show this help message and exit

EXAMPLES
  deckctl terminal prompt use starship

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl terminal tmux

```text
usage: deckctl terminal tmux [-h] {status,apply} ...

NAME
  deckctl terminal tmux — Manage terminal tmux operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {status,apply}
    status        Inspect the managed tmux configuration and available executable.
    apply         Apply the project’s managed tmux configuration.

options:
  -h, --help      show this help message and exit

EXAMPLES
  deckctl terminal tmux status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl terminal tmux status

```text
usage: deckctl terminal tmux status [-h]

NAME
  deckctl terminal tmux status — Inspect the managed tmux configuration and available executable.

DESCRIPTION
  Read-only. Does not create or stop tmux sessions.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl terminal tmux status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl terminal tmux apply

```text
usage: deckctl terminal tmux apply [-h]

NAME
  deckctl terminal tmux apply — Apply the project’s managed tmux configuration.

DESCRIPTION
  Writes user configuration; existing sessions may require reloading the config.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl terminal tmux apply

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl controller

```text
usage: deckctl controller [-h]
       {status,recommend,discover,capture,install-templates,open} ...

NAME
  deckctl controller — Manage controller operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {status,recommend,discover,capture,install-templates,open}
    status              List captured controller layouts and detect Valve source
                        templates.
    recommend           Recommend a Steam Input layout strategy for a game, application,
                        or emulator.
    discover            Find personal Steam Input VDF exports in Steam Controller
                        Configs.
    capture             Copy a selected VDF layout into the project’s named controller-
                        layout collection.
    install-templates   Install captured layouts and available Valve desktop layout into
                        Steam’s templates directory.
    open                Open the Steam controller-configuration page for a numeric App
                        ID.

options:
  -h, --help            show this help message and exit

EXAMPLES
  deckctl controller status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl controller status

```text
usage: deckctl controller status [-h]

NAME
  deckctl controller status — List captured controller layouts and detect Valve source templates.

DESCRIPTION
  Read-only. Does not create directories or alter Steam Input state.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl controller status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl controller recommend

```text
usage: deckctl controller recommend [-h] [--system SYSTEM] target

NAME
  deckctl controller recommend — Recommend a Steam Input layout strategy for a game, application, or emulator.

DESCRIPTION
  Read-only guidance. Community rankings are not automatically selected.

positional arguments:
  target           Host address for registration, or game/application title for
                   controller advice.

options:
  -h, --help       show this help message and exit
  --system SYSTEM  Emulation system identifier used to tailor the recommendation.

EXAMPLES
  deckctl controller recommend "World of Warcraft"

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl controller discover

```text
usage: deckctl controller discover [-h]

NAME
  deckctl controller discover — Find personal Steam Input VDF exports in Steam Controller Configs.

DESCRIPTION
  Read-only. Export a layout in Steam first if none are listed.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl controller discover

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl controller capture

```text
usage: deckctl controller capture [-h] --source SOURCE name

NAME
  deckctl controller capture — Copy a selected VDF layout into the project’s named controller-layout collection.

DESCRIPTION
  Writes a copy and metadata under ~/.config/deckctl/controller-layouts. Does not change the currently active per-game layout.

positional arguments:
  name             Name of the registered object, bundled profile, or capture; see
                   DESCRIPTION and EXAMPLES.

options:
  -h, --help       show this help message and exit
  --source SOURCE  Existing local source file or directory; see DESCRIPTION for the
                   required format.

EXAMPLES
  deckctl controller capture "My Layout" --source ~/layout.vdf

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl controller install-templates

```text
usage: deckctl controller install-templates [-h]

NAME
  deckctl controller install-templates — Install captured layouts and available Valve desktop layout into Steam’s templates directory.

DESCRIPTION
  Copies templates without editing live per-game state. Steam normally discovers them when entering Gaming Mode; restart Steam only if its picker remains cached.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl controller install-templates

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl controller open

```text
usage: deckctl controller open [-h] appid

NAME
  deckctl controller open — Open the Steam controller-configuration page for a numeric App ID.

DESCRIPTION
  Launches a steam:// URL through xdg-open. Requires Steam and a graphical session.

positional arguments:
  appid       Numeric Steam application ID whose controller page should open.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl controller open 12345

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl library

```text
usage: deckctl library [-h] {audit,repair} ...

NAME
  deckctl library — Manage library operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {audit,repair}
    audit         Inspect Steam shortcut targets, exact duplicates, artwork slots and
                  managed Desktop icons.
    repair        Preview or apply backed-up repairs for known Desktop icons and exact
                  duplicate Steam shortcuts.

options:
  -h, --help      show this help message and exit

EXAMPLES
  deckctl library audit

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl library audit

```text
usage: deckctl library audit [-h] [--json]

NAME
  deckctl library audit — Inspect Steam shortcut targets, exact duplicates, artwork slots and managed Desktop icons.

DESCRIPTION
  Read-only. Uses every discovered Steam account independently. Missing or unresolved targets are reported without executing them. Use library repair to review safe repairs; SteamGridDB remains the Gaming artwork owner.

options:
  -h, --help  show this help message and exit
  --json      Emit machine-readable JSON instead of the human-readable report.

EXAMPLES
  deckctl library audit --json

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl library repair

```text
usage: deckctl library repair [-h] [--yes] [--duplicates] [--user USER]

NAME
  deckctl library repair — Preview or apply backed-up repairs for known Desktop icons and exact duplicate Steam shortcuts.

DESCRIPTION
  Without --yes, preview only. --duplicates opts into removing byte-equivalent parsed records within each Steam account; --user limits those Steam repairs to one account. Steam must be closed for VDF edits. Original files are retained under state/shortcut-rollback. Missing executables are reported, never guessed. Gaming artwork remains owned by SteamGridDB.

options:
  -h, --help    show this help message and exit
  --yes         Accept this command’s confirmation prompts; prerequisite checks still
                run.
  --duplicates  Include exact duplicate Steam records in the repair plan.
  --user USER   Limit Steam duplicate repairs to this userdata account ID.

EXAMPLES
  deckctl library repair --duplicates --yes

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl aliases

```text
usage: deckctl aliases [-h]

NAME
  deckctl aliases — List convenience shell aliases and the deckctl command each invokes.

DESCRIPTION
  Read-only. Aliases are installed by control-plane setup; open a new shell to load them.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl aliases

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl desktop

```text
usage: deckctl desktop [-h] {apply,status} ...

NAME
  deckctl desktop — Manage desktop operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {apply,status}
    apply         Install project-owned Desktop icons and repair known project shortcut
                  icon references.
    status        Inspect project Desktop icon files and known shortcut icon references.

options:
  -h, --help      show this help message and exit

EXAMPLES
  deckctl desktop apply

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl desktop apply

```text
usage: deckctl desktop apply [-h]

NAME
  deckctl desktop apply — Install project-owned Desktop icons and repair known project shortcut icon references.

DESCRIPTION
  Writes user icon files and known project .desktop entries only. SteamGridDB retains Gaming Mode artwork ownership.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl desktop apply

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl desktop status

```text
usage: deckctl desktop status [-h]

NAME
  deckctl desktop status — Inspect project Desktop icon files and known shortcut icon references.

DESCRIPTION
  Read-only. Reports missing or stale integration independently of Steam artwork.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl desktop status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl decky

```text
usage: deckctl decky [-h] {plugins,select,selected,install-selected,receipts,theme,css}
       ...

NAME
  deckctl decky — Manage decky operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {plugins,select,selected,install-selected,receipts,theme,css}
    plugins             Audit selected Decky plugins and Decky Loader readiness.
    select              Interactively choose the project’s desired Decky plugins.
    selected            Print the current desired Decky plugin selection.
    install-selected    Install selected plugins through Decky’s supported plugin-store
                        workflow. Includes the release additions once for older saved
                        selections; preserves later opt-outs and existing plugin
                        settings.
    receipts            Display recorded Decky plugin installation receipts.
    theme               Manage decky theme operations.
    css                 Manage decky css operations.

options:
  -h, --help            show this help message and exit

EXAMPLES
  deckctl decky plugins

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl decky plugins

```text
usage: deckctl decky plugins [-h]

NAME
  deckctl decky plugins — Audit selected Decky plugins and Decky Loader readiness.

DESCRIPTION
  Read-only. Checks real plugin structure; an orphaned plugin directory does not prove Loader is active.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl decky plugins

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl decky select

```text
usage: deckctl decky select [-h]

NAME
  deckctl decky select — Interactively choose the project’s desired Decky plugins.

DESCRIPTION
  Writes selection state. Installation is performed by install-selected or the normal installer.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl decky select

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl decky selected

```text
usage: deckctl decky selected [-h]

NAME
  deckctl decky selected — Print the current desired Decky plugin selection.

DESCRIPTION
  Read-only. Selection is distinct from successful installation.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl decky selected

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl decky install-selected

```text
usage: deckctl decky install-selected [-h] [--reinstall] [--dry-run] [--yes]

NAME
  deckctl decky install-selected — Install selected plugins through Decky’s supported plugin-store workflow. Includes the release additions once for older saved selections; preserves later opt-outs and existing plugin settings.

DESCRIPTION
  Requires functioning Decky Loader and network access. --dry-run plans only; --reinstall replaces existing selected plugins; --yes accepts applicable prompts. Failure is reported instead of inventing successful receipts.

options:
  -h, --help   show this help message and exit
  --reinstall  Reinstall selected Decky plugins even when currently installed.
  --dry-run    Show intended Decky plugin operations without installing them.
  --yes        Accept this command’s confirmation prompts; prerequisite checks still
               run.

EXAMPLES
  deckctl decky install-selected --dry-run

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl decky receipts

```text
usage: deckctl decky receipts [-h]

NAME
  deckctl decky receipts — Display recorded Decky plugin installation receipts.

DESCRIPTION
  Read-only. Receipts are historical evidence; use plugins to inspect current state.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl decky receipts

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl decky theme

```text
usage: deckctl decky theme [-h] {install,status} ...

NAME
  deckctl decky theme — Manage decky theme operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {install,status}
    install         Apply the project’s CSS component stack using CSS Loader.
    status          Inspect the project CSS component/palette status.

options:
  -h, --help        show this help message and exit

EXAMPLES
  deckctl decky theme install

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl decky theme install

```text
usage: deckctl decky theme install [-h]

NAME
  deckctl decky theme install — Apply the project’s CSS component stack using CSS Loader.

DESCRIPTION
  Compatibility entry point for decky css apply. Bubble Gum Rave is a palette applied to supported settings, never a standalone fake theme.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl decky theme install

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl decky theme status

```text
usage: deckctl decky theme status [-h]

NAME
  deckctl decky theme status — Inspect the project CSS component/palette status.

DESCRIPTION
  Read-only compatibility entry point. Use decky css status for the primary interface.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl decky theme status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl decky css

```text
usage: deckctl decky css [-h] {status,apply,guide,profiles,capture,restore} ...

NAME
  deckctl decky css — Manage decky css operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {status,apply,guide,profiles,capture,restore}
    status              Inspect installed Theme Store components, palette configuration,
                        and CSS Loader integration.
    apply               Obtain required real components through CSS Loader’s Theme Store
                        and apply the Bubble Gum Rave palette.
    guide               Explain the CSS Loader component and palette workflow.
    profiles            List live CSS Loader profiles and project-captured profile
                        copies.
    capture             Capture one named or all live CSS Loader profiles for recovery.
    restore             Restore one named or all captured CSS Loader profiles.

options:
  -h, --help            show this help message and exit

EXAMPLES
  deckctl decky css status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl decky css status

```text
usage: deckctl decky css status [-h]

NAME
  deckctl decky css status — Inspect installed Theme Store components, palette configuration, and CSS Loader integration.

DESCRIPTION
  Read-only. Checks persisted state and receipts; missing prerequisites remain visible.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl decky css status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl decky css apply

```text
usage: deckctl decky css apply [-h]

NAME
  deckctl decky css apply — Obtain required real components through CSS Loader’s Theme Store and apply the Bubble Gum Rave palette.

DESCRIPTION
  Uses the installed plugin’s native backend and advertised configurable controls. Validates persisted settings. Requires CSS Loader; unsupported controls are reported and no fake theme or raw Git clone is installed.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl decky css apply

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl decky css guide

```text
usage: deckctl decky css guide [-h]

NAME
  deckctl decky css guide — Explain the CSS Loader component and palette workflow.

DESCRIPTION
  Read-only guidance describing prerequisites, components, and profile recovery.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl decky css guide

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl decky css profiles

```text
usage: deckctl decky css profiles [-h]

NAME
  deckctl decky css profiles — List live CSS Loader profiles and project-captured profile copies.

DESCRIPTION
  Read-only. CSS profiles are separate from deckctl hardware profiles.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl decky css profiles

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl decky css capture

```text
usage: deckctl decky css capture [-h] [name]

NAME
  deckctl decky css capture — Capture one named or all live CSS Loader profiles for recovery.

DESCRIPTION
  Copies exact profile settings and assets into ~/.config/deckctl/css-profiles. Returns configuration-required when no live profile exists.

positional arguments:
  name        Name of the registered object, bundled profile, or capture; see
              DESCRIPTION and EXAMPLES.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl decky css capture

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl decky css restore

```text
usage: deckctl decky css restore [-h] [name]

NAME
  deckctl decky css restore — Restore one named or all captured CSS Loader profiles.

DESCRIPTION
  Writes the live CSS profile directory and retains displaced profiles for rollback. Reload CSS Loader/Steam when instructed.

positional arguments:
  name        Name of the registered object, bundled profile, or capture; see
              DESCRIPTION and EXAMPLES.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl decky css restore

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl android

```text
usage: deckctl android [-h] {status,install,retry,repair,reinstall} ...

NAME
  deckctl android — Manage android operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {status,install,retry,repair,reinstall}
    status              Inspect real Waydroid image, installation, and readiness state.
    install             Launch the established SteamOS Waydroid installer.
    retry               Complete Android setup using the existing image when available.
    repair              Run the established protected Waydroid host-integration repair.
    reinstall           Deliberately recreate Android through the upstream protected
                        archive workflow.

options:
  -h, --help            show this help message and exit

EXAMPLES
  deckctl android status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl android status

```text
usage: deckctl android status [-h] [--json]

NAME
  deckctl android status — Inspect real Waydroid image, installation, and readiness state.

DESCRIPTION
  Read-only. An existing shortcut alone does not prove Android is installed.

options:
  -h, --help  show this help message and exit
  --json      Emit machine-readable JSON instead of the human-readable report.

EXAMPLES
  deckctl android status --json

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl android install

```text
usage: deckctl android install [-h]

NAME
  deckctl android install — Launch the established SteamOS Waydroid installer.

DESCRIPTION
  Uses the protected vendor workflow. Choose Android 13 with Google Play when prompted. If user state is missing after installation, opens the bundled launcher; close Android after first-run setup to resume provisioning. May request sudo; Google login remains interactive.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl android install

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl android retry

```text
usage: deckctl android retry [-h]

NAME
  deckctl android retry — Complete Android setup using the existing image when available.

DESCRIPTION
  Skips READY installations. For an existing image without user state, opens Android_Waydroid_Cage.sh in Desktop Mode. Close Android to resume provisioning. If the launcher is missing, runs protected host repair. Fresh installs use the vendor wizard. Never downloads a replacement image merely because user state is missing.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl android retry

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl android repair

```text
usage: deckctl android repair [-h]

NAME
  deckctl android repair — Run the established protected Waydroid host-integration repair.

DESCRIPTION
  Preserves the upstream protected repair and Android data. May request sudo and stop/restart services. Opens the bundled launcher afterward only if first-run user state is missing.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl android repair

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl android reinstall

```text
usage: deckctl android reinstall [-h]

NAME
  deckctl android reinstall — Deliberately recreate Android through the upstream protected archive workflow.

DESCRIPTION
  Disruptive operation: launches the baseline reinstall flow and its state-protection prompts. Prefer retry or repair for ordinary recovery.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl android reinstall

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl workspace

```text
usage: deckctl workspace [-h] {status,setup,notion-mcp} ...

NAME
  deckctl workspace — Manage workspace operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {status,setup,notion-mcp}
    status              Inspect optional Notion, ChatGPT, and Claude desktop-style web
                        applications.
    setup               Create the optional workspace web applications and Desktop
                        shortcuts.
    notion-mcp          Print guidance for connecting a supported agent to Notion MCP.

options:
  -h, --help            show this help message and exit

EXAMPLES
  deckctl workspace status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl workspace status

```text
usage: deckctl workspace status [-h] [--json]

NAME
  deckctl workspace status — Inspect optional Notion, ChatGPT, and Claude desktop-style web applications.

DESCRIPTION
  Read-only. Does not verify account login or service availability.

options:
  -h, --help  show this help message and exit
  --json      Emit machine-readable JSON instead of the human-readable report.

EXAMPLES
  deckctl workspace status --json

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl workspace setup

```text
usage: deckctl workspace setup [-h]

NAME
  deckctl workspace setup — Create the optional workspace web applications and Desktop shortcuts.

DESCRIPTION
  Writes browser app launchers and intentional Desktop icons. Each service requires its own account authentication.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl workspace setup

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl workspace notion-mcp

```text
usage: deckctl workspace notion-mcp [-h]

NAME
  deckctl workspace notion-mcp — Print guidance for connecting a supported agent to Notion MCP.

DESCRIPTION
  Read-only. Does not create credentials or authorize account access.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl workspace notion-mcp

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl setup

```text
usage: deckctl setup [-h] {run,status,report,open,cleanup,reset} ...

NAME
  deckctl setup — Manage setup operations using the commands below.

DESCRIPTION
  Choose a subcommand for its prerequisites, expected results, and effects. Help never performs the operation.

positional arguments:
  {run,status,report,open,cleanup,reset}
    run                 Resume incomplete guided setup or retry a named step.
    status              Show guided setup progress and how to resume.
    report              Report component readiness, interrupted operations and exact
                        retry commands.
    open                Open the persistent setup launcher in the desktop environment.
    cleanup             Remove verified, unchanged installer shortcuts staged by this
                        project.
    reset               Clear recorded guided-setup completion for a named step or all
                        steps.

options:
  -h, --help            show this help message and exit

EXAMPLES
  deckctl setup run

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl setup run

```text
usage: deckctl setup run [-h] [--step STEP]

NAME
  deckctl setup run — Resume incomplete guided setup or retry a named step.

DESCRIPTION
  Rechecks actual component state before skipping. --step ID selects one step; interrupted/failed/deferred states persist. A missing component cannot be marked complete. Required account/GUI interaction remains visible. READY is detected; CONFIRMED is user-confirmed configuration. Exit 2 means incomplete setup.

options:
  -h, --help   show this help message and exit
  --step STEP  Guided setup step ID; omit to reset all recorded progress.

EXAMPLES
  deckctl setup run --step android

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl setup status

```text
usage: deckctl setup status [-h]

NAME
  deckctl setup status — Show guided setup progress and how to resume.

DESCRIPTION
  Read-only. Does not create a shortcut or mark steps complete.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl setup status

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl setup report

```text
usage: deckctl setup report [-h] [--json]

NAME
  deckctl setup report — Report component readiness, interrupted operations and exact retry commands.

DESCRIPTION
  Read-only; --json gives structured output. READY requires a detector; CONFIRMED identifies user-confirmed account setup. Failed, stale or deferred steps remain visible. Exit 2 means setup needs attention, 1 means recorded module failure. Module readiness is rechecked; JSON also includes the last apply attempt.

options:
  -h, --help  show this help message and exit
  --json      Emit machine-readable JSON instead of the human-readable report.

EXAMPLES
  deckctl setup report --json

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl setup open

```text
usage: deckctl setup open [-h]

NAME
  deckctl setup open — Open the persistent setup launcher in the desktop environment.

DESCRIPTION
  May refresh the setup shortcut and launch a terminal. Requires a graphical Desktop Mode session.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl setup open

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl setup cleanup

```text
usage: deckctl setup cleanup [-h] [--dry-run]

NAME
  deckctl setup cleanup — Remove verified, unchanged installer shortcuts staged by this project.

DESCRIPTION
  Runs automatically after module provisioning and guided steps. Rechecks actual component readiness and file hashes; keeps incomplete installs, modified/untracked files, symlinks, application launchers, recovery copies and unrelated Downloads/ZIP files. Exact legacy EmuDeck downloader copies are recognized. --dry-run reports without deleting. This is not a general disk cleaner.

options:
  -h, --help  show this help message and exit
  --dry-run   Show intended Decky plugin operations without installing them.

EXAMPLES
  deckctl setup cleanup --dry-run

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl setup reset

```text
usage: deckctl setup reset [-h] [step]

NAME
  deckctl setup reset — Clear recorded guided-setup completion for a named step or all steps.

DESCRIPTION
  Changes progress bookkeeping only; does not uninstall applications or delete account data.

positional arguments:
  step        Guided setup step ID; omit to reset all recorded progress.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl setup reset

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

## deckctl help

```text
usage: deckctl help [-h] [command ...]

NAME
  deckctl help — Display the full manual entry for any registered command or command group.

DESCRIPTION
  Read-only. Equivalent to adding --help at the selected command level. Unknown command paths return usage error 2.

positional arguments:
  command     Command path to document, for example: decky css apply.

options:
  -h, --help  show this help message and exit

EXAMPLES
  deckctl help decky css apply

FILES
  ~/.config/deckctl/       Desired state, selected plugins, captured profiles.
  ~/.local/state/deckctl/  Receipts, recovery records, and update history.
  ~/.local/share/steamdeck-workstation/  Persistent releases and current link.
  DECKCTL_CONFIG and DECKCTL_STATE override shared config/state paths; some
  vendor integrations use their established fixed paths under HOME.

EXIT STATUS
  0  Operation/report completed. Read per-item states in diagnostic reports.
  1  Operation failed, or a required component is absent.
  2  Invalid command usage or a documented configuration-required state.
  Vendor subprocess errors may propagate their own nonzero status.

SEE ALSO
  deckctl help; deckctl verify; docs/COMMANDS.md; man deckctl
```

