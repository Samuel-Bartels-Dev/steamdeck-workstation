# Agent Instructions

This repository provisions and operates Steam Deck systems.

## Read first

1. `docs/PRINCIPLES.md`
2. `docs/ai/COMMON.md`
3. The active task under `tasks/active/`, if one exists.
4. The `README.md` for any module you modify.

## Repository rules

- Preserve SteamOS immutability. Do not introduce `pacman`/read-only-root modifications without an approved ADR.
- Every feature belongs to a module or shared `deckctl` library; do not place domain logic in `install.sh`.
- Module actions must be idempotent or explicitly document why they cannot be.
- `verify` must never mutate the system. Repairs belong in `doctor` or `apply`.
- Do not commit credentials, tokens, cookies, SSH private keys, BIOS/firmware binaries, ROMs, or personal saves.
- Hardware differences belong in profiles/capabilities, not duplicated OLED/LCD code paths.
- Interactive authentication/setup is a valid `CONFIG_REQUIRED` state.
- Modify only files required by the current task.
- Run `./bin/deckctl repo validate` plus relevant module tests before declaring work complete.

## Module rule

When working under `modules/<name>/`, read `modules/<name>/README.md` and `modules/<name>/module.json` first.

Nested `AGENTS.md` files are only appropriate when a subtree has engineering rules that differ from these defaults.
