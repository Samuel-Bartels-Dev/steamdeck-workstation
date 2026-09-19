# Architecture

## Layers

```text
bootstrap.sh -> obtains a release
install.sh   -> first-run provisioning entry point
deckctl      -> lifecycle/orchestration CLI
modules      -> domain implementations
profiles     -> desired state / hardware and usage overlays
state        -> local runtime facts under ~/.local/state/deckctl
```

## Module contract

Each top-level module contains `module.json`, `README.md`, action scripts, and tests. `module.json` declares dependencies and supported actions. `deckctl` topologically orders modules and invokes actions; it does not embed EmuDeck/Decky/Heroic-specific logic.

## Status model

- `READY`: desired capability is healthy.
- `CONFIG_REQUIRED`: software may be staged/installed, but user authentication or vendor GUI setup remains.
- `DEGRADED`: usable with a known issue.
- `NOT_INSTALLED`: capability is absent.
- `FAILED`: a concrete failure prevents normal operation.
- `OPTIONAL`: an intentionally optional capability is available to configure but does not block readiness.

## Storage model

- Internal NVMe: SteamOS, launchers, prefixes, caches, dev environment, WoW/stateful or performance-sensitive titles.
- `DECK-GAMES`: bulk PC game payloads from Steam/Heroic/other launchers.
- `DECK-EMU`: ROMs, BIOS/firmware source material, and EmuDeck library payloads.
- Critical saves/configuration: backed up separately and versioned.

## Game front-end model

Steam Game Mode is the front door. Heroic is a Desktop Mode install/update backend for Epic/GOG/Amazon; Battle.net is integrated through a non-Steam launcher workflow; EmuDeck favorites, Moonlight, chiaki-ng, and optional browser-based media services can be surfaced in Steam.

## Android gaming boundary

Android/Waydroid is an optional enhanced capability with privileged host integration. It is independently repairable and must never be a dependency of core Steam, gaming, emulation, remote, backup, or development modules.


## Media boundary

Streaming services are optional browser-backed Steam shortcuts. Chrome is the shared runtime; provider credentials and DRM/session state remain provider/browser-owned. Media setup must never become a dependency of core gaming, emulation, remote access, backup, or development.

## Cross-platform companion deliverables

The repository may contain companion tooling for systems the Deck depends on, but Deck provisioning never executes code for another platform.

`host/windows/` is the first example. It contains the Sunshine host companion kit. `deckctl remote host-kit` packages it for a registered Windows gaming PC. It is pulled/copied and executed on Windows independently. This preserves one source of truth without coupling SteamOS provisioning to Windows host mutation.

## Lifecycle completion

Before 1.0, the platform treats the following as first-class lifecycle operations rather than one-off setup notes:

- Steam Input template capture/reuse,
- EmuDeck storage migration using the owner-supported migration workflow,
- Steam shortcut/artwork audit,
- versioned backup plus selective restore,
- Flatpak permission recovery via Flatseal,
- network diagnostics and unified health reporting.
