# v0.2.32 — On-demand coding workspace and terminal tools

The installer now opens a staged setup builder so each person can choose the
parts of the workstation they want. It groups optional modules into play,
workstation, and everyday/connected stages, then offers a separate desktop-app
selection. Steam Deck Desktop Mode uses KDE's native selection dialogs; command
line sessions have a text fallback. The review page explains the plan before it
is saved. Choosing options does not install or remove software. Unselected
stages stay out of provisioning and do not count as setup failures. Run
`deckctl setup customize` later to revise a plan; use `--minimal` or `--defaults`
for a base-only or full-default plan. See the [setup builder guide](../README.md#choose-only-the-stages-you-want).

The terminal module adds Ghostty, Neovim, OpenCode and keeps its existing tmux
installation. `deckctl ai-workspace install` configures the tools, verifies and
installs Ollama wholly in user space, then pre-pulls `qwen2.5-coder:1.5b`.

Use `deckctl ai-workspace open` for a foreground local session. It starts its own
loopback engine with `OLLAMA_KEEP_ALIVE=0`, then terminates that server and its
runners when the session exits or receives handled termination signals. No AI
login/background service is installed. Model unload-after-response is requested;
this does not promise an exact delay or purge operating-system caches. The
ChatGPT Pro option uses OpenCode browser sign-in; do not paste a browser token.
See [workspace docs](../modules/ai-workspace/README.md).

The base desktop integration now repairs the Moonlight and Battle.net application
icons with bundled SVGs while preserving their existing commands. The SteamGridDB
artwork files are left in place.

## Validation scope

Contracts use isolated fake engines and temporary homes/process groups. Downloaded
Ghostty 1.3.1/OpenCode 1.18.31 version commands and Neovim 0.12.5 headless runtime
were checked from `/tmp`; no terminal tools or Ollama were installed on the Deck
for this change. Real Ollama model pull/inference and account login are untested.
