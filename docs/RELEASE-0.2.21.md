# v0.2.21 — installer preflight compatibility fix

The v0.2.20 installer could stop before provisioning with
`test_generated_manual_has_no_drift`: Python 3.13 wraps argparse synopsis text
differently from the Python 3.12 used to generate the packaged manuals. The
reported mismatch was documentation whitespace, not a damaged download or
missing user configuration.

v0.2.21 canonicalizes synopsis whitespace while retaining every usage token and
all command descriptions, arguments, examples, and exit information. Manual
drift remains a release/installer gate. Tests verify that real documentation
changes are still detected. CI covers Python 3.12 and 3.13.

The installer explicitly labels pre-install checks and announces when provisioning
begins. The existing install flow, module selection, recovery, CSS/Decky/Desktop
work, and detailed command help remain intact; Waydroid is unchanged.

Extract the new USB ZIP, open its STEAMDECK-SETUP folder, and run:

```bash
bash ./INSTALL.sh
```

Do not reuse the v0.2.20 nested tar. No wipe is needed for the logged failure:
the checksum passed and pre-install tests stopped the run before provisioning.
Real hardware/vendor operations still need validation on the Steam Deck.
