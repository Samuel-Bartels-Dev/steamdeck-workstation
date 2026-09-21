# v0.2.35 — Individual setup tools

Every bundled software category has individual choices: terminal tools and appearance, Codex and development container, remote clients, workspace web apps, streaming shortcuts and KeeperFill, Ollama and local model download. Existing app, launcher, Decky plugin, and CSS component selectors remain available.

Choosing only Ghostty installs only Ghostty. Installation, readiness checks and guided setup honor selections. AI workspace requires OpenCode; selecting the local model includes Ollama. Older configurations retain legacy defaults until edited. Deselecting preserves existing software and settings.

No new background service is added by the selector. Tailscale remains an explicitly selectable persistent service. Browser web apps disclose their shared Chrome dependency.

The setup flow now distinguishes browsing from selection, starts fresh setups with an empty optional plan, provides search and breadcrumbs, and reviews actual selected items with edit links. Related Decky/CSS choices stay together. Installation results show readable states and nonzero operation exits instead of implying success.
