# New Deck Walkthrough

## Before wiping your current Deck

- Back up saves, emulator saves/states, WoW `WTF/` and `Interface/AddOns/`, and any non-cloud saves you care about.
- Have your private BIOS/firmware bundle available separately if you use emulation.
- Keep a copy of this release and checksum on USB.

## Fresh Steam Deck

1. Unbox/reset the Deck and complete Valve's normal first-run setup.
2. Connect to Wi-Fi and install all available **stable** SteamOS updates.
3. Reboot after updates.
4. Switch to **Desktop Mode**.
5. Connect a keyboard/mouse if convenient.
6. Copy the release folder/archive from USB to your home directory (for example `~/Downloads/steamdeck-workstation-0.2.26`).
7. Extract it if needed.
8. Open Konsole in the project folder.
9. Run:

```bash
chmod +x install.sh
./install.sh
```

10. The installer will detect hardware, validate the repo, install safe user-space packages, and stage interactive installers where required.
11. Complete the displayed checklist:
   - Tailscale authentication/install flow.
   - Decky stable installer, then curated plugins.
   - EmuDeck first-run wizard and storage selection.
   - Heroic account login and **Auto Add to Steam**.
   - Battle.net installation/login if desired.
   - chiaki-ng PS5 registration/PSN remote setup.
   - Moonlight pairing to Sunshine hosts.
   - Codex/other dev authentication.
12. Insert/identify `DECK-GAMES` and `DECK-EMU` cards as applicable.
13. Import your private BIOS/firmware material through the documented EmuDeck paths; do not put those files in this repo.
14. Run:

```bash
./bin/deckctl verify
./bin/deckctl travel check
```

15. Return to Game Mode.

## Important

The installer intentionally does not attempt to automate account logins or GUI flows that are likely to break across vendor updates. It stages and verifies them instead.

## Android / Pokémon Champions

When the guided runner reaches Android/Waydroid, choose **Android 13 with Google Play**. Let the Waydroid installer create its Steam shortcut. After setup, sign into Google Play inside Waydroid and install Pokémon Champions.


## Optional media apps

When guided setup reaches **Media Apps**, choose whether to create Netflix, Hulu, Crunchyroll, and Prime Video shortcuts. The helper installs Chrome if required and adds selected services to Steam. You can skip this step and run `./bin/deckctl media setup` later.
