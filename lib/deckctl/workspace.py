from __future__ import annotations
import json, subprocess
from pathlib import Path
from . import component_options
HOME=Path.home(); APPS=HOME/'.local/share/applications'; BINDIR=HOME/'.local/share/deckctl/workspace/bin'
SERVICES={'notion':('Notion','https://www.notion.so/'),'chatgpt':('ChatGPT','https://chatgpt.com/'),'claude':('Claude','https://claude.ai/')}
def _chrome(): return subprocess.run(['flatpak','info','com.google.Chrome'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
def setup(only=None):
    from .desktop import exec_line
    chosen=component_options.effective('workspace')
    if only is not None:
        if only not in chosen: raise ValueError('Workspace app is not selected')
        chosen={only}
    if not chosen: return 0
    APPS.mkdir(parents=True,exist_ok=True); BINDIR.mkdir(parents=True,exist_ok=True)
    if not _chrome():
        rc=subprocess.run(['flatpak','install','--user','-y','flathub','com.google.Chrome']).returncode
        if rc: return rc
    for sid,(name,url) in SERVICES.items():
        if sid not in chosen: continue
        runner=BINDIR/sid; desktop=APPS/f'deck-workspace-{sid}.desktop'
        runner.write_text(f'#!/usr/bin/env bash\nexec flatpak run com.google.Chrome --no-first-run --disable-session-crashed-bubble --app="{url}"\n'); runner.chmod(0o755)
        desktop.write_text(f'[Desktop Entry]\nType=Application\nName={name}\nComment={name} workspace app\nExec={exec_line([str(runner)])}\nIcon=web-browser\nTerminal=false\nCategories=Office;Network;\nStartupNotify=true\n'); desktop.chmod(0o755)
        print(f'[ready] {name}: {desktop}')
    from . import desktop as desktop_icons
    desktop_icons.apply()
    print('\nNotion automation: use Notion MCP from an authorized ChatGPT/Codex/Claude client. deckctl never stores the token.')
    return 0
def status(json_mode=False):
    data={sid:(APPS/f'deck-workspace-{sid}.desktop').exists() for sid in component_options.effective('workspace')}
    if json_mode: print(json.dumps(data,indent=2))
    else:
        print('Workspace apps\n--------------')
        for sid,(name,_) in SERVICES.items():
            if sid not in data: continue
            print(f"{name:10} {'READY' if data[sid] else 'MISSING'}")
    return 0 if all(data.values()) else 2
def notion_mcp():
    print('Notion MCP\n----------')
    print('Connect Notion MCP from ChatGPT/Codex, Claude, Cursor, or another authorized MCP client to read/write your Notion workspace.')
    print('Complete OAuth interactively and grant only intended workspace access. deckctl never stores the Notion token.')
    return 0

def verify():
    ready = all((APPS / f'deck-workspace-{sid}.desktop').is_file() for sid in component_options.effective('workspace'))
    print(json.dumps({'status': 'READY' if ready else 'CONFIG_REQUIRED',
                      'message': 'Workspace shortcuts ready' if ready else 'Run deckctl workspace setup'}))
    return 0
