# v0.2.42 — Install progress and shared appearance

The setup window shows the running item first, with its phase, elapsed time,
and received bytes for managed terminal downloads. Percentages require a known
server total. Extraction and provider operations show activity, not invented
percentages. View log opens bounded phase and error diagnostics; interactive
prompts stay in Konsole.

Theme & appearance applies one palette across selected Ghostty, Fastfetch,
Oh My Posh, Starship, Konsole, tmux and supported CSS Loader themes. Independent
switches preserve the current appearance when disabled and never install extra
tools. Personal Ghostty configuration is preserved. Appearance choices are
included in shared setup exports and validated before import.

See [setup sharing and resuming](setup/SHARING-AND-RESUME.md) and the
[terminal module](../modules/terminal/README.md) for configuration details.
