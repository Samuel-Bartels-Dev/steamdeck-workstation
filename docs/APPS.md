# Choose, install and remove desktop apps

The normal installer offers a chooser before provisioning. Choices are saved in
`~/.config/deckctl/apps.json` (or `$DECKCTL_CONFIG/apps.json`) and survive release
upgrades. Without a saved selection, all catalog apps remain enabled for compatibility.

| Key | App | Module |
| --- | --- | --- |
| `zen` | Zen Browser | Utilities |
| `flatseal` | Flatseal | Utilities |
| `zed` | Zed | Development |
| `vscode` | VS Code | Development |
| `vlc` | VLC | Media |
| `plex` | Plex Desktop | Media |
| `spotify` | Spotify | Media |
| `discord` | Discord | Utilities |
| `slack` | Slack | Utilities |

```bash
deckctl apps list                 # choices and installed status
deckctl apps select               # interactive chooser
deckctl apps select zen zed vlc   # replace the entire selection
deckctl apps select --none        # skip all catalog apps; keep existing installations
deckctl apps install              # install the saved selection
deckctl apps install spotify      # enable and install just Spotify
```

Selection alone never removes software. `deckctl apply` respects the saved choices
for enabled modules; `apps install` installs selected catalog apps directly,
regardless of the enabled module profile. Already installed user/system packages
are reused. Deselected apps do not fail module verification. Corrupt selection
files stop app provisioning instead of silently installing everything.

Gaming launchers, shared Chrome web-app dependencies, Codex, Distrobox, Docker,
Decky and vendor setup are outside this desktop app chooser. Their established
module/setup commands still apply. Selecting no editors does not disable the
Development module's other checks. App presence does not certify login or playback.

## Remove an app and keep settings

Close the app, then preview and apply an exact named removal:

```bash
deckctl apps uninstall spotify
deckctl apps uninstall spotify --yes
deckctl apps uninstall zen zed --yes
```

The preview changes nothing. `--yes` deselects the named apps and removes only
their user Flatpak installations. It does not pass `--delete-data`, remove
`~/.var/app/APP_ID`, delete downloaded media, force-close apps, prune runtimes,
or remove unrelated apps. System-only installations are refused before any
selection or package changes; manage those separately. If a system copy also
exists, removing the user copy does not remove the system copy.

An interrupted or failed uninstall leaves the app deselected so the next apply
cannot reinstall it. Rerun the uninstall to finish; an already absent app is safe
to repeat. Re-enable and reinstall with `deckctl apps install NAME`; retained
settings can be reused. This command intentionally provides no data-purge option.

Choices survive updates, but rolling back to releases before v0.2.30 restores
installers that do not understand these choices. Avoid running their provisioning
if you want to keep apps deselected.

Install Discord and Slack with `deckctl apps install discord slack`. Upgrades keep
existing saved selections; new apps are available in the chooser but must be
explicitly enabled when a selection already exists.
