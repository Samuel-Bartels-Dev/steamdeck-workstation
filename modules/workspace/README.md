# Workspace Apps

Use `deckctl setup customize` to choose individual tools in this category. Selections are saved in `~/.config/deckctl/components.json` and govern installation, verification, and guided setup. Deselecting a tool preserves existing installations and personal settings. Older setups without saved component choices retain their previous defaults.

Creates Chrome app-window shortcuts for Notion, ChatGPT, and Claude on SteamOS. Notion MCP is the recommended agent integration path. Tokens/credentials are never stored by deckctl.

## Desktop icons

Distinct bundled SVG icons are installed locally and applied to known project
shortcuts. Media/workspace launchers are also copied to the Desktop. Repair with
`deckctl desktop apply`; audit with `deckctl desktop status`. No Steam Gaming Mode
artwork files are touched; SteamGridDB remains their owner.

## Selected apps in Gaming Mode

ChatGPT installation also submits a non-Steam shortcut using SteamOS's existing
helper. Exact existing app targets are reused; pending submissions wait for Steam
refresh without duplicate additions. Retry/Resume verifies the saved shortcut.
Setup preserves Steam, account data, custom shortcuts and artwork, and never
switches sessions. See [Gaming Mode app shortcuts](../../docs/APPS.md#gaming-mode-shortcuts).
