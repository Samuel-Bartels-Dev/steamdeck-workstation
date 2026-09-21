# Base Module

Ensures Flatpak/Flathub and user-space state foundations exist without modifying SteamOS's immutable base image. It intentionally does not install Arch packages with `pacman`.

## Desktop icons

Distinct bundled SVG icons are installed locally and applied to known project
shortcuts, including Moonlight and Battle.net application-menu entries. If those
launchers exist, managed copies are added to the Desktop. Their launch commands
remain intact and SteamGridDB artwork files are not rewritten. Repair with
`deckctl desktop apply`; audit with `deckctl desktop status`.
