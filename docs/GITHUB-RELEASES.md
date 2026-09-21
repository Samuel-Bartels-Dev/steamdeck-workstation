# GitHub source and release distribution

Repository: https://github.com/Samuel-Bartels-Dev/steamdeck-workstation

The repository contains editable source, modules, tests and documentation.
Clone it in VS Code or use Git normally. Stable users should install published
release assets, which preserve the tested packaging and executable permissions.

## Internet installer

From Konsole in Desktop Mode, as your normal Deck user:

```bash
curl -fL https://raw.githubusercontent.com/Samuel-Bartels-Dev/steamdeck-workstation/main/bootstrap.sh -o /tmp/steamdeck-workstation-install.sh && bash /tmp/steamdeck-workstation-install.sh
```

The bootstrap resolves the latest stable GitHub release, downloads its tar and
checksums, verifies SHA-256 and archive structure, then runs the normal installer.
It fails before provisioning when assets are unavailable or invalid. The command
becomes usable once a public release with the required assets is published.
Use `--version 0.2.34` to select this release or `--download-only DIRECTORY` to
save verified download files without installation. Download-only directories must
not already contain those filenames. SHA-256 checks corruption against GitHub's
manifest; it is not a separate cryptographic publisher signature.

## Source development

```bash
git clone https://github.com/Samuel-Bartels-Dev/steamdeck-workstation.git
cd steamdeck-workstation
./bin/deckctl repo validate
./tools/build-release /tmp/deck-release
python3 tools/verify-release.py /tmp/deck-release
```

Changes on main and pull requests trigger validation and extracted-package tests
on Python 3.12 and 3.13. The separate Publish verified release workflow runs when VERSION changes on
main, and can also be manually triggered there. It packages and verifies before creating
the version tag/release and uploading exactly the three release artifacts. It
refuses to replace an existing release. Actions are pinned to reviewed commit SHAs.

The USB bundle remains supported: extract the complete STEAMDECK-SETUP directory
and run `bash INSTALL.sh`. USB delivery still needs internet for vendor payloads;
it is not a complete offline software cache.
