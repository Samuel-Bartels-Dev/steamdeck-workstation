# v0.2.33 — Choose your workstation setup

The installer now opens a staged setup builder before provisioning. Pick from
three optional feature groups — play and personalize, workstation and creation,
and everyday and connected — then choose desktop apps separately. On Steam Deck
Desktop Mode it uses native KDE dialogs; in a terminal it offers the same flow
as text questions. Defaults are preselected, a review page shows what will be
included, and the plan can be changed later.

Choosing options only saves desired state. It does not install or remove apps.
Base support stays enabled, dependencies and modules that own selected apps are
added automatically, and features you leave out do not count as setup failures.
Use `deckctl setup customize --minimal` for a base-only plan or
`deckctl setup customize --defaults` to restore the full repository defaults.
See the [setup builder guide](../README.md#choose-only-the-stages-you-want).

## Validation scope

Python syntax, runtime help, generated-command documentation, local documentation
links, and whitespace checks passed. The full static linter was unavailable in
the current environment because Ruff, ShellCheck and actionlint are not installed.
CI runs the repository's complete regression suite.
