# Testing Strategy

## Contract tests

`tests/contract/test_repo.py` validates module manifests, required documentation, action paths, dependency references, and cycles.

## Static checks

Run:

```bash
./bin/deckctl repo validate
```

CI runs Ruff, ShellCheck, actionlint, local Markdown link checks, generated manual checks, contract/configuration tests, secret-pattern scanning and dependency/security checks. Windows companion scripts are parsed under PowerShell 5.1 and 7 without executing provisioning. Full Markdown style lint and shfmt migration remain deferred.

## Hardware validation

A capability may be implemented before it is physically verified. Track actual OLED/LCD validation separately; do not claim an LCD path is validated only because OLED tests pass.

## Safety

Tests must not modify the SteamOS root image. Destructive integration tests require explicit opt-in.

See [production operations](PRODUCTION-OPERATIONS.md) for SAFE diagnostics, test harness modes, release gates and physical evidence requirements.
