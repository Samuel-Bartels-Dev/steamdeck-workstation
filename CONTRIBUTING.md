# Contributing

1. Start with a scoped task under `tasks/active/`.
2. Read `AGENTS.md`, `docs/PRINCIPLES.md`, and the target module README/manifest.
3. Keep domain logic in the owning module; keep `deckctl` orchestration generic.
4. Add or update verification/tests.
5. Run `./bin/deckctl repo validate` before committing.
6. Do not commit private game content, BIOS/firmware binaries, saves, tokens, or credentials.
