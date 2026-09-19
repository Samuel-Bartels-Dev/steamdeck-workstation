from __future__ import annotations
import json, os, re, shutil, subprocess
from pathlib import Path
from . import core

CAPTURE_DIR = Path.home()/'.config/deckctl/controller-layouts'
TEMPLATE_DIR = Path.home()/'.local/share/Steam/controller_base/templates'
STEAM_BASE = Path.home()/'.local/share/Steam/controller_base'

def _slug(s:str):
    return re.sub(r'[^A-Za-z0-9._-]+','-',s).strip('-') or 'layout'

def status():
    print('CONTROLLER PROFILE MANAGER')
    print(f"Steam templates     {'READY' if TEMPLATE_DIR.exists() else 'NOT INITIALIZED'}")
    captured=sorted(CAPTURE_DIR.glob('*.vdf'))
    print(f"Captured layouts    {len(captured)}")
    for p in captured: print(f"- {p.name}")
    valve=[]
    for name in ('desktop_neptune.vdf','gamepad_with_joystick_trackpad_neptune.vdf'):
        if (STEAM_BASE/name).exists(): valve.append(name)
    print(f"Valve source layouts {', '.join(valve) if valve else 'not detected yet'}")

def recommend(target:str, system:str|None=None):
    t=target.lower()
    if system:
        print(f"Recommended: EmuDeck profile for {system} when provided; otherwise Gamepad with Joystick Trackpad.")
        print('Why: EmuDeck documents special Steam Input profiles for several emulators and uses Gamepad with Joystick Trackpad as the safe fallback.')
    elif any(x in t for x in ('netflix','hulu','prime','crunchy','media')):
        print('Recommended: Deck Desktop Mouse / desktop-style layout.')
        print('Why: right trackpad/touch input is more useful than a pure gamepad for browser-backed media UI.')
    elif any(x in t for x in ('pokemon champions','waydroid','android')):
        print('Recommended: Gamepad with Joystick Trackpad, plus touchscreen.')
        print('Why: battles can use gamepad input while Android menus may still need pointer/touch input.')
    elif any(x in t for x in ('world of warcraft','wow')):
        print('Recommended: Gamepad with Joystick Trackpad + ConsolePort in WoW.')
        print('Why: ConsolePort owns in-game controller UX; trackpad remains a mouse fallback for launcher/addon UI.')
    elif any(x in t for x in ('moonlight','chiaki','playstation')):
        print('Recommended: Gamepad with Joystick Trackpad / developer default.')
        print('Why: preserve normal gamepad forwarding; only add trackpad mouse fallback if needed.')
    else:
        print('Recommended priority: Developer Recommended -> known-good captured template -> Gamepad with Joystick Trackpad -> guided Community Layout.')
        print('deckctl does not automatically choose today\'s highest-ranked Community Layout because rankings and compatibility change.')

def discover():
    root=Path.home()/'.local/share/Steam/steamapps/common/Steam Controller Configs'
    if not root.exists():
        print('Steam Controller Configs directory not found yet. Export a layout as New Personal Save in Game Mode first.')
        return
    files=sorted(root.glob('*/config/**/*.vdf'))
    if not files:
        print('No exported VDF layouts found.')
        return
    for p in files:
        print(p)

def capture(name:str, source:str):
    src=Path(os.path.expanduser(source)).resolve()
    if not src.exists() or src.suffix.lower()!='.vdf': raise SystemExit('Source must be an existing .vdf file')
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    dest=CAPTURE_DIR/f'{_slug(name)}.vdf'
    shutil.copy2(src,dest)
    meta=CAPTURE_DIR/f'{_slug(name)}.json'
    meta.write_text(json.dumps({'name':name,'source':str(src)},indent=2)+'\n')
    print(f'Captured {name} -> {dest}')

def install_templates():
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    installed=[]
    # Preserve exact Valve VDF content; copying into templates is reversible and avoids editing live per-game state.
    valve_desktop=STEAM_BASE/'desktop_neptune.vdf'
    if valve_desktop.exists():
        dst=TEMPLATE_DIR/'Deck Desktop Mouse.vdf'; shutil.copy2(valve_desktop,dst); installed.append(dst)
    for src in sorted(CAPTURE_DIR.glob('*.vdf')):
        dst=TEMPLATE_DIR/src.name; shutil.copy2(src,dst); installed.append(dst)
    if not installed:
        print('No layouts available to install. Export/capture one first, or start Steam once so Valve desktop_neptune.vdf exists.')
        return 1
    print('Controller templates installed successfully:')
    for p in installed: print(f'- {p}')
    print('No restart is required during the initial Desktop Mode setup.')
    print('Continue provisioning normally. When you later switch to Game Mode, Steam reloads and should discover the template.')
    print('If the template picker was already open/cached and the template is still missing in Game Mode, restart Steam once as a fallback.')
    return 0

def open_controller(appid:str):
    if not str(appid).isdigit(): raise SystemExit('APPID must be numeric')
    url=f'steam://controllerconfig/{appid}'
    if shutil.which('xdg-open'):
        subprocess.Popen(['xdg-open',url],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); print(url); return 0
    print(url); return 1
