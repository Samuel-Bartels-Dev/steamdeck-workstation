# v0.2.31 — Discord and Slack

Adds Discord (`com.discordapp.Discord`) and Slack (`com.slack.Slack`) to the
Utilities module and desktop app chooser using user Flathub packages.

```bash
deckctl apps install discord slack
```

Existing saved app selections stay unchanged. Choose the new apps explicitly
when upgrading; fresh installs offer both in the normal chooser. Already installed
packages are reused. Missing selected apps are reported by verification.

`deckctl apps uninstall discord` or `deckctl apps uninstall slack` previews
removal; append `--yes` to remove the user app, keep settings and prevent reinstall.

The existing module contract tests now exercise both apps, including missing-app
verification and repeated installs. Account login, calls, screen sharing and Slack
workspace access remain separate from installation verification.
