# Steam Deck Workstation v0.2.44-rc4

This candidate includes all rc3 installer fixes and adds optional
[TinyFingers](https://tinyfingers.net/) to Websites in Game Mode.

Select TinyFingers in setup to create a persistent fullscreen Chrome launcher
and submit it to the already-running Steam account. Existing website choices,
Chrome profile and Steam shortcuts stay preserved. Pending handoffs remain
retryable until Steam saves the exact target; setup never restarts Steam or
switches sessions. Existing TinyFingers runners are preserved on Retry.

Hardware acceptance: confirm one TinyFingers tile under Non-Steam, launch it in
Gaming Mode, check touchscreen/mouse/keyboard and sound, then Retry/Resume after
Steam refresh. Browser parent controls and Steam Input remain interactive;
installer completion does not prove gameplay or controller mapping.

Automated regression, repository lint, packaging and public installer checks
are distinct from physical Deck launch/input verification.
