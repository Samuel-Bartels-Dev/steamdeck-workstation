#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
missing=()
desktop_app_satisfied com.github.tchx84.Flatseal || missing+=("Flatseal")
desktop_app_satisfied app.zen_browser.zen || missing+=("Zen Browser")
desktop_app_satisfied com.discordapp.Discord || missing+=("Discord")
desktop_app_satisfied com.slack.Slack || missing+=("Slack")
desktop_app_satisfied com.ktechpit.whatsie || missing+=("WhatsApp (Whatsie)")
desktop_app_satisfied org.telegram.desktop || missing+=("Telegram")
if (( ${#missing[@]} )); then
  module_json NOT_INSTALLED "Missing desktop apps: ${missing[*]}; rerun deckctl apply"
else
  module_json READY "Selected utility apps satisfied"
fi
