---
name: Bug report
about: Report an installation, upgrade, provisioning or recovery problem
title: "[Bug]: "
---

Before reporting, check the [compatibility record](../../docs/COMPATIBILITY.md)
and [community guide](../../docs/COMMUNITY.md). Maintainers can use the
[hardware checklist](../../docs/HARDWARE-TESTING.md) to reproduce release issues.

## What happened?

Describe the actual result and what you expected. Include the exact failed
command or installer step and its exit status if available.

## Environment

- Steam Deck Workstation version (and commit if using a checkout):
- SteamOS version/build and stable/beta/preview channel:
- Steam Deck LCD or OLED (no serial number):
- Steam client build/channel:
- Fresh install, same-version rerun, or upgrade from which version:
- GitHub bootstrap, tar, or USB ZIP:
- Relevant plugin/application versions:
- Internal storage or card labels involved (no private paths):

## Steps to reproduce

1.
2.
3.

Does repeating the same step fail again? What was the last known working release?

## Diagnostic evidence

Paste the smallest relevant error excerpt after removing private information.
`deckctl setup report` can identify an incomplete step and its retry command.
For Android include `deckctl android status`; for other commands check `--help`.
Do not retry destructive operations just to gather a log.

A support bundle is optional: run `deckctl support-bundle` and inspect the output
locally before attaching it. Sanitization is not a substitute for your review.
Never attach passwords, tokens, cookies, private keys, account identifiers, private
host addresses, ROMs, BIOS, save files, browser profiles or backup archives.

## Recovery / workaround

Describe what you tried and whether user data was affected. Do not post private
file contents. For suspected vulnerabilities, avoid publishing exploit details
or secrets in a public issue; consult the repository's security guidance.

## Before submitting

- [ ] I checked existing issues and the compatibility record.
- [ ] I removed sensitive information from text, screenshots and attachments.
- [ ] I distinguished a required login/pairing step from a software failure.
