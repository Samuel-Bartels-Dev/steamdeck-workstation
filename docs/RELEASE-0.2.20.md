# Steam Deck Workstation v0.2.20

Repository review and command documentation release, based on immutable v0.2.19.

- [Engineering review, fixes, evidence, and remaining boundaries](ENGINEERING-REVIEW-0.2.20.md)
- [Complete command manual](COMMANDS.md)
- [Installer and maintenance script reference](SCRIPTS.md)

The normal installation flow remains unchanged: initial Valve setup, Desktop
Mode, obtain the release, run the installer, and complete unavoidable vendor
and account prompts. Existing hardware/vendor subsystems remain integrated.

Validation includes the original regression contracts, 28 existing behavioral
tests, 30 review tests, and help execution for all 124 parser pages. Packaging
uses the established tar and USB wrapper, with independent extraction, source
inventory/mode comparison, nested tar identity, and SHA-256 verification.

Live hardware, account authentication, streaming, and vendor installs remain
outside this build environment's test coverage. Waydroid code is unchanged.
