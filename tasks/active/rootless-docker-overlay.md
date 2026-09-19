# Rootless Docker overlay repair

Fix the Docker 29 container creation failure observed on a Steam Deck OLED:
the rootless daemon starts, but containerd overlay mounts return invalid argument.

Scope: explicit, persistent fuse-overlayfs compatibility selection for the
managed engine; preserve old storage and refuse a switch while it is active.
Keep SteamOS immutable and remote/context engines unchanged. Include actionable
diagnostics, regression coverage, and a live managed-engine build/HTTP test.

Validation: container contracts, repository validation, lint where tools are
available, and Docker/Compose/Buildx on the affected Steam Deck.
