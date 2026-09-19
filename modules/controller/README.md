# Controller profile manager

Manages **known-good Steam Input templates and captured personal layouts** without editing Steam's live per-game controller state blindly.

Principles:
- Prefer Valve/developer recommended layouts for normal Steam games.
- Prefer EmuDeck-provided Steam Input profiles for emulators when EmuDeck documents one.
- Use `Gamepad with Joystick Trackpad` as the safe general fallback.
- Media/Android benefit from a desktop/mouse-style template.
- Captured `.vdf` files are copied into `~/.config/deckctl/controller-layouts/` and can be installed into Steam's templates directory.
- Applying a layout to a specific game remains a Steam UI confirmation; deckctl opens the relevant controller page rather than rewriting active Steam state.

Commands:
- `deckctl controller status`
- `deckctl controller recommend <target> [--system SYSTEM]`
- `deckctl controller discover`
- `deckctl controller capture NAME --source FILE.vdf`
- `deckctl controller install-templates`
- `deckctl controller open APPID`

## Fresh-install behavior

During `deckctl setup run`, template installation is a synchronous reconciliation step rather than an interactive installer. It copies the available VDF templates, verifies the expected file exists, and continues automatically. No Steam restart is required while the initial Desktop Mode setup is still running. Switching to Game Mode later reloads Steam; restart Steam only if the template is still not visible after that transition.
