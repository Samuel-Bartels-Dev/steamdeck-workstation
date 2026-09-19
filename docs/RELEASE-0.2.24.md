# v0.2.24 — preserve installer input permissions

The v0.2.23 installer changed every module shell file to executable before
running validation. This included `modules/terminal/terminal.sh`, which is sourced
configuration and intentionally has mode 0644. Preservation checks then correctly
reported 0755 (decimal 493) versus 0644 (decimal 420) and stopped provisioning.

The blanket chmod is removed. Release tarballs already preserve executable modes;
validation still rejects incorrectly packaged files. The sourced terminal file
and all runtime modules remain byte-for-byte identical to v0.2.23.

Use the freshly extracted v0.2.24 release with the normal installer. No wipe is
needed. The reported v0.2.23 run stopped before control-plane installation or
module provisioning. Existing-install support, verified installer cleanup,
CSS selection/palette, Waydroid first-launch and recovery features remain.

The regression suite executes the installer's preflight prefix in an isolated
shell fixture, verifies unchanged file modes, and reproduces the old chmod
failure in a separate disposable copy. Vendor provisioning and physical Steam
Deck behavior are not executed by the container tests. Existing live Theme Store
validation limitations remain.
