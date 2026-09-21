# Development

Use `deckctl setup customize` to choose individual tools in this category. Selections are saved in `~/.config/deckctl/components.json` and govern installation, verification, and guided setup. Deselecting a tool preserves existing installations and personal settings. Older setups without saved component choices retain their previous defaults.

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

## Zed

Also installs **Zed** from the community-maintained
[Flathub package](https://flathub.org/apps/dev.zed.Zed) (`dev.zed.Zed`). This is
independent of VS Code, Codex and Distrobox. Existing user/system Flatpak installs
are reused; missing Zed is reported by verification. Project access, editor
extensions and account sign-in are configured inside Zed by the user.

## App choices and removal

The desktop Flatpaks in this module are selectable with `deckctl apps select`.
Only selected apps are installed and required by verification; existing apps are
kept when deselected. `deckctl apps uninstall NAME` previews a user-app removal;
add `--yes` to remove it while preserving settings and disabling reinstalls.
See [app management](../../docs/APPS.md). Other module features are independent.
