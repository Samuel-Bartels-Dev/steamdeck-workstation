# Claude Code Entry Point

Canonical engineering guidance lives in repository documentation; do not duplicate it here.

Read, in order:
- `docs/PRINCIPLES.md`
- `docs/ai/COMMON.md`
- the active task under `tasks/active/`, if present
- the target module's `README.md` and `module.json`

Follow the same constraints documented in `AGENTS.md`. Keep changes scoped, preserve SteamOS immutability, never commit secrets/private emulation content, and run `./bin/deckctl repo validate` plus relevant tests.
