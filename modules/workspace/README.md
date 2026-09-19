# Workspace Apps

Creates Chrome app-window shortcuts for Notion, ChatGPT, and Claude on SteamOS. Notion MCP is the recommended agent integration path. Tokens/credentials are never stored by deckctl.

## Desktop icons

Distinct bundled SVG icons are installed locally and applied to known project
shortcuts. Media/workspace launchers are also copied to the Desktop. Repair with
`deckctl desktop apply`; audit with `deckctl desktop status`. No Steam Gaming Mode
artwork files are touched; SteamGridDB remains their owner.
