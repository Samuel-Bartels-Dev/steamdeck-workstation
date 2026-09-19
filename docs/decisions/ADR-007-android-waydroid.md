# ADR-007 — Android Gaming via SteamOS-specific Waydroid

## Status
Accepted for v0.1.2.

## Decision
Use the SteamOS-targeted `pjohno/steamos-waydroid-bundle` integration rather than generic Arch/Waydroid instructions. Treat Android as a separately repairable module because it performs privileged host integration that may need repair after SteamOS atomic updates.

For Pokémon Champions, recommend the normal Android 13 + Google Play path, not experimental Android 16.

## Rationale
- SteamOS requires ABI-aware host packages instead of assuming a normal mutable Arch host.
- The selected installer verifies compatible bundles before modifying the host.
- Its Android 13 path supplies ARM translation required by ARM-only applications on the Deck's x86-64 CPU.
- It can preserve Android image/user state while repairing host integration after SteamOS updates.

## Consequences
- Android compatibility is best-effort and not vendor-supported by Valve or The Pokémon Company.
- The module must remain noncritical: failure must not break Steam, emulation, remote gaming or development.
- Never bypass the upstream compatibility/fingerprint safety checks in normal provisioning.
