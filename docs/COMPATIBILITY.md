# Compatibility record

A passing CI run is not proof that vendor installers or SteamOS hardware work.
Record exact versions and evidence; never turn an untested cell into PASS.

| Project revision | Environment | Evidence | Result and limit |
| --- | --- | --- | --- |
| v0.2.26; source commit `cb426679f1009fd39a835f3cb034c8d5c3dc9ae1` | GitHub Ubuntu runners, Python 3.12 and 3.13 | [Release regression run](https://github.com/Samuel-Bartels-Dev/steamdeck-workstation/actions/runs/35409442993) | Automated regression and package verification passed; no Deck hardware or live vendor-install certification. |
| PR #1; source commit `f05804e4636167a6259ae10ee0795ae9cb373a94` | GitHub Ubuntu runners, Python 3.12 and 3.13 | [Regression/package run](https://github.com/Samuel-Bartels-Dev/steamdeck-workstation/actions/runs/35410835003), [lint run](https://github.com/Samuel-Bartels-Dev/steamdeck-workstation/actions/runs/35410835043) | CI passed; runtime files unchanged by the PR. |
| v0.2.26 | Steam Deck LCD/OLED, SteamOS exact build not recorded | No release-scoped hardware report committed yet | NOT TESTED here. User troubleshooting successes are not a complete release certification. |

## Vendor boundaries

| Integration | Requirement to record in a hardware report |
| --- | --- |
| Android / Waydroid | Exact SteamOS version/build, bundle target/revision, image type, successful Android launch and Google Play interaction. READY alone does not prove Google Play works. |
| Decky and plugins | Loader version, Steam client channel/build, requested plugin versions and actual load results. Store presence is not compatibility. |
| CSS Loader | Plugin version, Theme Store component versions, controls discovered and visible palette result. Bubble Gum Rave is configuration, not a theme package. Colored Toggles is not requested. |
| EmuDeck and storage | Installer/manager version, filesystem and card label, migration verification and a save/load test. No ROMs or BIOS in evidence. |
| Remote and media | Client/host versions and an actual connection or playback test. Pairing and service login remain user interactions. |

## Updating this record

Use the [hardware checklist](HARDWARE-TESTING.md). Add a row per tested
release/SteamOS/model/install-path combination with a public PR/issue or committed
sanitized report. Use PASS, FAIL, BLOCKED, NOT TESTED, or NOT APPLICABLE with a
reason. A partial test certifies only the named features. Keep historical rows;
link a superseding report instead of overwriting old failures.

Minimum report: release and commit, SteamOS version/build/channel, Deck model,
Steam client build/channel, fresh install or source upgrade version, relevant
vendor versions, result per check, date, and remaining limitations. Never include
serial numbers, account identifiers, host addresses, credentials or private data.
