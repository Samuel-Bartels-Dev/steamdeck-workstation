# Development

Provides the lightweight local development surface for the Deck.

## Codex

Codex CLI is installed directly as a user-level Linux tool. It intentionally does **not** depend on Distrobox or npm inside the container. Installation uses OpenAI's standalone Linux installer first and falls back to the latest official `openai/codex` Linux x86_64 release artifact if necessary.

Authentication remains interactive:

```bash
codex login
codex login status
```

The verifier requires a runnable Codex binary and reports authentication separately.

## deck-dev

Distrobox remains useful for project dependencies and disposable build tooling. `deck-dev` is created from the checked-in `distrobox.ini` when Distrobox and Podman are available. Failure of the container layer must not prevent Codex itself from being installed.

## VS Code

VS Code is installed as a Flatpak and is independent of the Codex CLI.
