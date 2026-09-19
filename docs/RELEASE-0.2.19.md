# v0.2.19 release scope and validation

This release is a patch of the supplied v0.2.18 archive, not a project rebuild.
Baseline SHA-256: `e924bc7791701fc68e46bdac68f0daa81d11c71f49cd3f4a20ff9af7ccc97420`.

The baseline file inventory is recorded in `tests/fixtures/baseline-v0.2.18.json`.
Its required-file checks cover all retained modules; unchanged-file hashes protect
159 files. All Android/Waydroid files are unchanged. Existing terminal functionality
is unchanged apart from its HTTP User-Agent reading the release VERSION dynamically.
The seven removed files belong only to the incorrect standalone CSS palette theme.
The exact originals' hashes remain available for conservative migration detection.

## Automated gates

- `./bin/deckctl repo validate`: baseline contract/regression checks and 28 added
  behavioral/static tests for native CSS configuration and persistence, repeat runs,
  unavailable/incompatible components, profile capture/restore, UI safe mode,
  Desktop icons, media kiosk/submission behavior, Decky detection/archive identity,
  support-bundle exclusions, baseline file integrity, shell/Python/JSON syntax,
  registration and executable permissions.
- `./tools/build-release OUTPUT`: validate first, then create the exact repo tar,
  USB ZIP, and external SHA-256 manifest. The USB ZIP has its own nested-repo checksum.
- `./tools/verify-release.py OUTPUT`: independently extract the standalone and USB
  nested tar; compare complete file/mode inventories; run the full repository suite
  in both extractions; verify ZIP CRCs/layout, executable entry points, versions,
  nested archive identity, junk exclusions and final checksums.

## Limits of this release's build environment

Physical Steam Deck UI rendering, sudo/service restarts on SteamOS, real account
sign-ins, and live vendor installs are not executed by the isolated regression
suite. The live CSS Theme Store and Decky Store returned HTTP 403 from the build
environment. Native CSS tests use the published API/storage contract and four real
Chromahon control schemas (107 configured color controls); they do not claim a
successful live Store download. The installer reports actual download/API failures
and never records configuration readiness from a success message alone.

CSS Loader upstream changes can require an adapter update. Unknown interfaces,
ambiguous Store names, unknown color controls, and locally edited legacy themes are
reported explicitly. Existing completed components survive a retry. Optional layout
themes and vendor/account authentication retain their existing ownership.
