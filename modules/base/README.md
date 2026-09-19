# Base Module
Ensures Flatpak/Flathub and user-space state foundations exist without modifying SteamOS's immutable base image. It intentionally does not install Arch packages with `pacman`.

## Desktop icons

Distinct bundled SVG icons are installed locally and applied to known project
shortcuts. Media/workspace launchers are also copied to the Desktop. Repair with
`deckctl desktop apply`; audit with `deckctl desktop status`. No Steam Gaming Mode
artwork files are touched; SteamGridDB remains their owner.
