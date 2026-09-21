#!/usr/bin/env bash
set -euo pipefail
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
app_status=0
desktop_app_install com.github.tchx84.Flatseal || app_status=1
desktop_app_install app.zen_browser.zen || app_status=1
desktop_app_install com.discordapp.Discord || app_status=1
desktop_app_install com.slack.Slack || app_status=1
desktop_app_install com.ktechpit.whatsie || app_status=1
desktop_app_install org.telegram.desktop || app_status=1
exit "$app_status"
