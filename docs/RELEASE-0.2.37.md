# v0.2.37 — Setup guidance and section flow

The sidebar follows Gaming → Desktop apps → Coding & work → Remote & storage → Review → Install & finish. Each section has a short explanation. Review edits return to the matching section.

Every curated option has a practical description explaining what it does, why to choose it, and relevant requirements. These include tools, desktop apps, launchers, Decky plugins and CSS Loader components. Descriptions also appear in review. Installer and theme policies are unchanged; presentation copy lives in config/setup-copy.json.

Native UI flow tests cover the reordered sections and review links at desktop, compact and minimum window sizes. Catalog coverage checks require an explanatory blurb for every curated option.

## More individual apps and terminal artwork

- Add Parsec, Telegram and WhatsApp (Whatsie, a clearly labeled third-party client).
- Keep Slack and Plex Desktop available as independent choices.
- Give the `ff` shell helper compact red Sharingan-inspired ASCII artwork when
  fastfetch is selected. Preserve personal Fastfetch settings.
- Verify independent app selection and repeat installation without extra downloads.

See [app management](APPS.md) and [terminal setup](../modules/terminal/README.md).

## Setup previews

![Desktop app choices](screenshots/setup-desktop-apps.png)

![Compact setup window](screenshots/setup-compact.png)

The **Bubble Gum Rave** Fastfetch theme pairs pink keys, cyan/purple section
headings and pale text with the red Sharingan eye. It shows SteamOS, model,
kernel, uptime, CPU/GPU, RAM/swap, battery, available home/external storage,
display and desktop/shell information. Hardware fields appear when detected.
The optional Konsole appearance choice supplies the matching dark background;
the Fastfetch theme works in other terminals too.

The managed theme is `~/.config/deckctl/terminal/fastfetch.json`.
After updating, select fastfetch and Shell helpers, run
`deckctl terminal apply --config-only`, then open a new shell and run `ff`.
It is a snapshot on demand, with no background monitor.
