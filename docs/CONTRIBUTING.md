# Contributing and PR guardrails

Open a pull request against `main`. Keep changes scoped and follow
[the engineering principles](PRINCIPLES.md). Runtime changes need behavioral
coverage; verification must not mutate the Deck.

## Local checks

Use Python 3.12 or 3.13 in a Git checkout. Install development tools in a virtual
environment **outside the repository** so they cannot enter release archives:

```bash
python3 -m venv ../sdw-lint-env
source ../sdw-lint-env/bin/activate
python -m pip install -r .github/lint-requirements.txt
```

Install [actionlint 1.7.7](https://github.com/rhysd/actionlint/releases/tag/v1.7.7)
for your platform, verifying the release checksum, and put it on `PATH`.
Then run:

```bash
python3 tools/lint-repo.py
./bin/deckctl repo validate
```

The lint command checks tracked files, including extensionless Python and shell
entry points. Stage new files with `git add` before running it. It is read-only
and does not install software. `--help` documents requirements and exit codes.

## What CI checks

- **Static checks:** Ruff Python correctness rules, Bash syntax, ShellCheck errors
  and warnings, actionlint workflow syntax/expressions and embedded shell checks,
  local documentation links, and generated command-help consistency.
- **regression (3.12)** and **regression (3.13):** existing behavioral and baseline
  preservation tests, actual release builds, clean archive extraction and package
  verification, plus the existing secret-pattern check.

Python unused-import and unused-local cleanup is deferred; formatting is not a
merge gate. ShellCheck has four narrowly scoped exclusions in the lint runner:
interactive `cat` arguments are supplied by users (SC2120), `mkcd` returns the
last `cd` status (SC2164), an existing unused installer flag (SC2034), and literal
`~/DeckBackups` diagnostic text (SC2088). Other warnings still fail. Review these
exceptions when the corresponding scripts change. No protected runtime files
were rewritten merely to satisfy lint.

CI tools are version-pinned, actionlint's download is checksum-verified, actions
are pinned to commit SHAs, and the new PR job has read-only permissions, no stored
checkout credentials, a timeout, and cancellation of obsolete runs. It uses
`pull_request`, never privileged `pull_request_target` execution of PR code.

## Recommended repository settings

These are **administrator settings**, not automatically enabled by this PR:

1. Protect `main`: require pull requests and the three successful checks above;
   require the branch to be up to date and conversations resolved. Block force
   pushes and deletion. Select check names after their first successful run.
2. Require an independent approving review when another maintainer is available;
   dismiss stale approvals after new commits. Avoid requiring your own approval
   on a one-maintainer project.
3. Enable GitHub secret scanning and push protection where available. The existing
   regex check only catches a few known patterns; it is not a complete secret scanner.

Branch protection is what makes checks mandatory for merging. A green workflow
alone does not enforce that policy. GitHub-hosted tests cannot prove SteamOS
hardware behavior or live vendor availability: changes to Android initialization,
Decky APIs, storage migration or controller integration still need a documented
Deck smoke test. Keep release publishing separate from PR checks.

## Security and UI checks

- **CodeQL (python/actions):** scan Python and workflow code on PRs, main and
  weekly. Findings appear in GitHub code scanning; a successful scan is not
  proof there are no vulnerabilities.
- **Dependency vulnerability review:** fail PRs introducing known high/critical
  dependency vulnerabilities. Requires GitHub's dependency graph.
- **Python tool vulnerability audit:** check CI Python requirements against
  vulnerability advisories, including on the weekly schedule.
- **Installer UI smoke:** exercise the real Qt window offscreen at three sizes,
  including individual app/model selections and saving; no vendor installations.
- **Dependabot:** propose weekly updates for pinned actions and Python CI tools.

Actions are commit-pinned, checkout does not retain credentials, and untrusted PR
code does not run through `pull_request_target`. CodeQL alone receives permission
to upload security results. Existing lint, Docker, regression and archive
verification checks remain. Branch protection/required checks are repository
settings; these workflows do not change them. Enable the desired required checks
after their first successful run. The scans cover this repository and declared
dependencies, not every vendor binary downloaded later on a Deck.
