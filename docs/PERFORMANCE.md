# Performance and Battery Strategy

The default policy is conservative: use Valve's current SteamOS behavior first, then make per-game changes based on measured need.

## OLED

- 90 Hz is available; 45 FPS/90 Hz is a useful balanced target for games that cannot hold 90 FPS.
- 30 FPS divides cleanly into 90 Hz for heavy titles.
- Remote streaming can target 90 FPS when the host/network path can sustain it.

## LCD

- 60 Hz maximum display path.
- 40 FPS/40 Hz remains a useful balanced target when supported.
- Remote streaming normally targets up to 60 FPS.

## Do not apply globally by default

- forced GPU clocks
- SMT disabling
- UMA buffer changes
- swap/swappiness tweaks
- undervolting/overclocking
- legacy CryoUtilities-style blanket tuning

Install PowerTools for cases where a specific emulator/game benefits, and persist those settings per-title rather than globally. `deckctl profile` records desired operational profiles but v0.2.27 intentionally does not force global TDP/display changes.
