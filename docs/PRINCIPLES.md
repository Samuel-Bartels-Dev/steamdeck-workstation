# Engineering Principles

1. **Valve owns SteamOS.** Prefer supported user-space mechanisms over modifying the immutable base image.
2. **Desired state is data; execution is code.** Profiles describe what should exist. Modules implement it.
3. **Every feature is a module.** Modules expose a predictable contract and own their domain.
4. **`deckctl` orchestrates; modules implement.** Domain-specific installation logic does not belong in the root CLI.
5. **Hardware differences are profiles/capabilities, not forks.** OLED/LCD share implementation unless hardware truly requires otherwise.
6. **Interactive setup is a state, not a failure.** Authentication/GUI work may legitimately return `CONFIG_REQUIRED`.
7. **Verification is read-only.** `verify` reports; `doctor` repairs; `apply` converges desired state.
8. **Replaceable payloads and irreplaceable state are different.** Games can be re-downloaded; saves/configuration need protection.
9. **Secrets never enter Git or support bundles.** Redaction is mandatory.
10. **Strong interfaces, simple implementation.** Do not build a framework larger than the problem.
11. **Every important change is observable.** Modules must expose verification and meaningful diagnostics.
12. **Recovery is part of design.** Installer delivery, local recovery copy, backups, and travel readiness are first-class.
13. **Agent context uses progressive disclosure.** Root AI files are maps; module READMEs hold domain knowledge; tasks hold current scope.
14. **Adding a feature should be local.** A new launcher/tool should usually require one module/submodule plus configuration, not edits across the repository.
15. **Stable releases are deployment artifacts.** Normal Decks use known-good releases; development can track branches.

## Cross-platform isolation
Companion code for another machine may live in this repository, but the Steam Deck provisioning graph must never execute it. Windows Sunshine host tooling is packaged/exported explicitly and run on the Windows host by a human/operator.
