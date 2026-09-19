# First-Run Guided Setup

`install.sh` now launches `deckctl setup run` automatically. You should **not** need to browse to `~/Desktop/Deck-Setup-Staged` yourself.

The guided runner launches each GUI/vendor step in sequence and persists progress. If you stop midway, resume with either:

```bash
./bin/deckctl setup run
```

or double-click **Continue Steam Deck Setup** on the Desktop.

## Guided steps

1. **Heroic** — sign into Epic; enable **Add games to Steam automatically**. Use Heroic for installation/updates, then launch individual games from Steam Game Mode.
2. **Battle.net** — choosing Yes runs NonSteamLaunchers in targeted CLI mode with `"Battle.net"`, so there is no full launcher checklist. Complete Battle.net's installer/login, then install WoW/Diablo as desired and let NSL surface shortcuts.
3. **Decky** — install the latest stable loader. Curated plugin selection, installation, audit, CSS Loader Theme Store downloads and Bubble Gum Rave palette configuration are completed in Desktop Mode. Game Mode is used for a visual check and normal plugin use.
4. **EmuDeck** — complete the wizard; prefer `DECK-EMU` for the Emulation tree when using split storage.
5. **Tailscale** — the staged SteamOS-specific installer is launched; enter sudo when prompted and authenticate from the QR/login URL.
6. **Moonlight** — pair Sunshine hosts.
7. **chiaki-ng** — register PlayStation locally; test remote PSN connectivity later from a non-home network.

GUI account authentication and vendor wizard choices are intentionally not click-automated. `deckctl` automates discovery, launch, sequencing, persistence, and verification around those human-required steps.

## Useful commands

```bash
./bin/deckctl setup status
./bin/deckctl setup run
./bin/deckctl setup open
./bin/deckctl setup reset heroic
./bin/deckctl verify
```

## Android / Pokémon Champions

When the guided runner reaches Android/Waydroid, choose **Android 13 with Google Play**. Let the Waydroid installer create its Steam shortcut. After setup, sign into Google Play inside Waydroid and install Pokémon Champions.


## Optional media apps

When guided setup reaches **Media Apps**, choose whether to create Netflix, Hulu, Crunchyroll, and Prime Video shortcuts. The helper installs Chrome if required and adds selected services to Steam. You can skip this step and run `./bin/deckctl media setup` later.
