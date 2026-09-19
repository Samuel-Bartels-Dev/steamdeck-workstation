#!/usr/bin/env bash
source "$DECKCTL_ROOT/lib/deckctl/module.sh"
have lsblk || { module_json FAILED "lsblk missing"; exit 0; }
module_json READY "Storage discovery available; role cards are optional until inserted"
