## Why

Describe the problem and the user-visible result.

## Changes

Describe the scope, including any provisioning or stored-state changes.

## Validation

- [ ] `python3 tools/lint-repo.py` passes.
- [ ] `./bin/deckctl repo validate` passes.
- [ ] PR regression and package verification jobs pass on Python 3.12 and 3.13.
- [ ] Security/dependency checks and installer UI smoke pass.
- [ ] Space checks, current-version skips and failed-update recovery are covered when downloads change.
- [ ] New behavior has a regression test that checks resulting state.

## Upgrade and recovery review

Mark items not applicable with a brief reason; CI does not replace this review.

- [ ] Fresh install and an already-configured Deck can both converge safely.
- [ ] Re-running provisioning skips verified work and retries incomplete work.
- [ ] Verification stays read-only; repairs are explicit.
- [ ] Personal data, credentials, and recovery copies remain protected.
- [ ] Command behavior changes include help and generated manual updates.
- [ ] Baseline preservation exceptions are explained, not silently broadened.
- [ ] Android, Decky/CSS, Desktop icons and SteamGridDB responsibilities remain intact.

## Risks and rollback

State any hardware checks still needed and how to recover from a failed change.
