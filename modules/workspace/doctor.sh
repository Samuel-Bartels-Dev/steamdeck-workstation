#!/usr/bin/env bash
PYTHONPATH="$DECKCTL_ROOT/lib" python3 -c 'from deckctl.workspace import status,notion_mcp; status(); notion_mcp()'
