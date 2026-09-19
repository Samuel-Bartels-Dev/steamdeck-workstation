# Common AI Engineering Context

The project is an endpoint-management layer for Steam Deck, not a custom SteamOS distribution.

## Context discipline

- Read only the active task, target module README/manifest, and referenced ADRs unless broader context is required.
- Do not recursively inspect the whole repository by default.
- Use `deckctl ai context <module>` to discover the intended scoped context.

## Change discipline

- Preserve module boundaries.
- Prefer configuration/data additions over new branches of hard-coded behavior.
- Add tests and verification for every meaningful capability.
- Do not make `verify` mutate state.
- Do not silently change a user's performance settings, storage layout, or personal data.
