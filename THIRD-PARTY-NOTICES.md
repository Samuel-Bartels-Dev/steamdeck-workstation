# Third-party notices and license scope

The root [MIT License](LICENSE) applies to Steam Deck Workstation's original
code and documentation. It does not relicense third-party software, assets,
metadata, trademarks or services. Preserve upstream terms and attribution when
redistributing them. This is a scoped source review, not a claim that every
external application's license has been audited.

## Bundled upstream-derived test metadata

These fixtures contain transcribed/projected control metadata, not upstream CSS
or executable theme code. They are used offline to test API/control discovery;
runtime themes still come through CSS Loader's Theme Store.

| Local material | Upstream author/source | License evidence and treatment |
| --- | --- | --- |
| `tests/fixtures/css/steamDeckThemes.Chromahon-SM.json` | [mugenmono, Chromahon-SM](https://github.com/mugenmono/steamDeckThemes.Chromahon-SM) | Upstream declares GPL-3.0; retained [upstream license](LICENSES/Chromahon-SM-GPL-3.0.txt). Derived metadata is excluded from the root MIT grant. |
| `tests/fixtures/css/steamDeckThemes.Chromahon-CM.json` | [mugenmono, Chromahon-CM](https://github.com/mugenmono/steamDeckThemes.Chromahon-CM) | Upstream declares GPL-3.0; retained [upstream license](LICENSES/Chromahon-CM-GPL-3.0.txt). Derived metadata is excluded from the root MIT grant. |
| `tests/fixtures/css/steamDeckThemes.Chromahon-QAM.json` | [mugenmono, Chromahon-QAM](https://github.com/mugenmono/steamDeckThemes.Chromahon-QAM) | No repository license detected during review. Permission to redistribute any protectable expression is unresolved; do not assume MIT or a sibling project's GPL applies. |
| `tests/fixtures/css/steamDeckThemes.Chromahon-Controls.json` | [mugenmono, Chromahon-Controls](https://github.com/mugenmono/steamDeckThemes.Chromahon-Controls) | No repository license detected during review. Same unresolved status as QAM. |
| `tests/fixtures/css/focus-highlight.json` | [FlanGrande, FocusHighlightColor](https://github.com/FlanGrande/SteamDeckFlanTheme/tree/main/FocusHighlightColor) | Upstream MIT; retain [upstream copyright and license](LICENSES/FlanGrande-MIT.txt). |

Reviewed 2026-09-19 against the public upstream repositories. The retained GPL
license files both have upstream Git blob ID
`f288702d2fa16d3cdf0035b15a9fcbc552cd88e7`; the MIT notice has blob ID
`1185a7a18aed23414dfa34306677057e7ea7e5a4` and retains its original
`Copyright (c) 2022 suchmememanyskill` line. Original provenance
is also recorded in the [CSS fixture notes](tests/fixtures/css/README.md) and
[Focus Highlight source notes](tests/fixtures/css/focus-highlight-SOURCE.md).
The fixtures transform theme manifests into a CSS Loader backend response shape;
they are not verbatim full themes. Their existing data and regression tests are
unchanged by this licensing PR.

**Unresolved follow-up:** obtain explicit licensing clarification for the QAM
and Controls metadata, or replace it with independently authored contract
fixtures while retaining meaningful schema coverage. Until that review is
resolved, this repository must not be described as entirely MIT-licensed or as
having fully cleared third-party redistribution rights. Adding notices alone
does not resolve missing permissions. No new release is published by this PR.

## Software obtained at install time

The integrations below download, install, configure or invoke separate upstream
products. Their software is not relicensed by this project. Consult the license
shipped with the exact downloaded version; plugin/theme authors may use different
terms from their loader. This list describes major integrations, not a complete
transitive dependency inventory.

- [Decky Loader](https://github.com/SteamDeckHomebrew/decky-loader),
  [Decky installer](https://github.com/SteamDeckHomebrew/decky-installer), and
  individually authored plugins from the Decky Store.
- CSS Loader and individually authored Theme Store components, including the
  Chromahon components and DellyVolume. Bubble Gum Rave is configuration.
- [SteamOS Waydroid bundle](https://github.com/pjohno/steamos-waydroid-bundle),
  Waydroid, Android images, and Google Play services where selected.
- [EmuDeck](https://www.emudeck.com/) and separately distributed emulators.
- [NonSteamLaunchers](https://github.com/moraroy/NonSteamLaunchers-On-Steam-Deck),
  Heroic, Battle.net, Steam and other selected game launchers.
- Starship, Oh My Posh, zoxide, JetBrains Mono/Nerd Fonts, tmux and other terminal
  tools installed through their upstream sources/package managers.
- Moonlight, Sunshine, Tailscale, browsers and other Flatpak applications.

Google Play, streaming services and game stores retain their own terms and
account requirements. This project's license grants no rights to games, ROMs,
BIOS images, firmware, subscription content or vendor branding. Bundled simple
Desktop shortcut icons identify launch targets; names and marks remain with
their respective owners and imply no endorsement.

## Contributors and distributors

Record the source, author, exact version/commit when known, license and local
path for any new copied code or assets. Include required upstream notices and
source obligations. A download URL or public GitHub repository is not itself a
license. Review redistribution terms before bundling external payloads into a
release rather than obtaining them from their normal installer sources.
