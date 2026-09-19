# Security and Private Data

Never commit or include in support bundles:

- Steam, Epic, GOG, Amazon, Battle.net, PSN, Tailscale, GitHub, Codex, or other credentials/tokens.
- Browser profiles/cookies.
- SSH private keys or Sunshine private certificates.
- BIOS/firmware binaries, ROMs, disc images, or other copyrighted game payloads.
- Personal save archives unless explicitly placed in a private backup destination.

The repository stores only manifests, checksums/metadata, documentation, scripts, and non-secret preferences.

`deckctl support-bundle` writes a redacted diagnostic archive. Review it before sharing externally.

## Restore and Windows host kits
- Restore archives are local/private state and must not be committed to Git.
- Generated Windows host kits may contain hostnames, MAC addresses, and tailnet target names. Treat generated kits as private operational artifacts even though the generic `host/windows/` scripts are safe to version.
- Host scripts do not contain Sunshine passwords, Tailscale auth keys, or other credentials.
