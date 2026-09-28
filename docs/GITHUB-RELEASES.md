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

The default bootstrap clones the newest `main` commit with `git`, validates the
checkout, then runs the normal installer. Each main commit uses its own local
control-plane directory, and the previous one remains available for rollback.
This follows source changes immediately; it is not a fixed, checksum-verified
release. `git` and Python 3 are required.

Use `bash /tmp/steamdeck-workstation-install.sh --version 0.2.43` for a fixed
published release instead. That mode downloads the release tar and checksums,
verifies SHA-256 and archive structure, then runs the normal installer.
`--download-only DIRECTORY` also requires `--version`. Download-only directories must
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
main, and can also be manually triggered there. RC versions publish as prereleases. Stable publication now requires a reviewed evidence report through manual workflow input; a stable VERSION push alone is blocked. See [production release gates](PRODUCTION-OPERATIONS.md). It packages and verifies before creating
the version tag/release and uploading exactly the three release artifacts. It
refuses to replace an existing release. Actions are pinned to reviewed commit SHAs.

The USB bundle remains supported: extract the complete STEAMDECK-SETUP directory
and run `bash INSTALL.sh`. USB delivery still needs internet for vendor payloads;
it is not a complete offline software cache.
