# Testing Strategy

## Contract tests

`tests/contract/test_repo.py` validates module manifests, required documentation, action paths, dependency references, and cycles.

## Static checks

Run:

```bash
./bin/deckctl repo validate
```

When available, CI should also run ShellCheck, secret scanning, JSON schema validation, Markdown link checking, and Python syntax checks.

## Hardware validation

A capability may be implemented before it is physically verified. Track actual OLED/LCD validation separately; do not claim an LCD path is validated only because OLED tests pass.

## Safety

Tests must not modify the SteamOS root image. Destructive integration tests require explicit opt-in.
