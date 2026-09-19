# v0.2.25 — requested Decky plugins

Adds Game Theme Music, MagicPods and TabMaster to the recommended Store selection.
Promotes Controller Tools from optional and corrects its official Store name.
Bluetooth remains recommended. Older saved selections gain these five requests
once; later explicit opt-outs persist. Other selected plugins, settings and
unmanaged plugins are preserved. Dry runs, status and cancelled installs do not
write selection state. Missing Store packages remain reported for retry.

Use the normal installer on an existing Deck; no wipe is needed. Plugins are
installed through the existing official Store catalog/CDN path with identity
validation and atomic replacement. The earlier preflight isolation, permission
fix and verified installer cleanup remain. Waydroid, CSS components and palette,
Desktop icons, SteamGridDB ownership and recovery implementations are unchanged.

Offline tests cover migration, opt-outs, no-op installs, cancellation, dry runs,
Store failures and validated package installation/retry. Live Store access is
blocked in the build environment; physical SteamOS/plugin compatibility remains
an on-device check. New plugin preferences use the native plugin interfaces.
