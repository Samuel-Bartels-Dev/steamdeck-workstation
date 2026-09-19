"""Bundled Desktop Mode icons. Never reads or writes Steam's artwork directories."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from . import core

ICONS = {'setup', 'media', 'netflix', 'hulu', 'crunchyroll', 'prime-video', 'notion', 'chatgpt', 'claude'}
ENTRIES = {
    'Continue Steam Deck Setup.desktop': 'setup',
    'Media-Apps.desktop': 'media',
    **{f'deck-media-{sid}.desktop': sid for sid in ('netflix', 'hulu', 'crunchyroll', 'prime-video')},
    **{f'deck-workspace-{sid}.desktop': sid for sid in ('notion', 'chatgpt', 'claude')},
}


def desktop_dir():
    if shutil.which('xdg-user-dir'):
        result = subprocess.run(['xdg-user-dir', 'DESKTOP'], capture_output=True, text=True, timeout=5)
        candidate = Path(result.stdout.strip())
        if result.returncode == 0 and candidate.is_absolute() and candidate != Path.home():
            return candidate
    return Path.home() / 'Desktop'


def icon_path(icon):
    if icon not in ICONS:
        raise ValueError('Unknown managed Desktop icon: ' + icon)
    return Path.home() / '.local/share/icons/hicolor/scalable/apps' / f'deckctl-{icon}.svg'


def install_icon(icon):
    source = core.ROOT / 'modules/base/icons' / f'{icon}.svg'
    target = icon_path(icon)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = source.read_bytes()
    if not target.is_file() or target.read_bytes() != payload:
        temporary = target.with_suffix('.svg.tmp')
        temporary.write_bytes(payload)
        temporary.chmod(0o644)
        temporary.replace(target)
    return target


def _with_icon(text, path):
    lines = text.splitlines()
    start = lines.index('[Desktop Entry]')
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith('[')), len(lines))
    indices = [i for i in range(start + 1, end) if lines[i].startswith('Icon=')]
    if indices:
        lines[indices[0]] = f'Icon={path}'
        for i in reversed(indices[1:]):
            del lines[i]
    else:
        lines.insert(start + 1, f'Icon={path}')
    return '\n'.join(lines) + '\n'


def apply():
    for icon in sorted(ICONS):
        install_icon(icon)
    home = Path.home()
    desktop = desktop_dir()
    roots = [home / '.local/share/applications', home / 'Desktop/Deck-Setup-Staged', home / 'Desktop', desktop]
    handled = set()
    for root in roots:
        for name, icon in ENTRIES.items():
            path = root / name
            if path in handled or not path.is_file() or path.is_symlink():
                continue
            handled.add(path)
            old = path.read_text()
            new = _with_icon(old, icon_path(icon))
            if old != new:
                path.write_text(new)
            path.chmod(0o755)
            # App launchers are surfaced on the Desktop too. Staged vendor installers
            # remain in their existing folder; no unrelated .desktop files are touched.
            if name.startswith(('deck-media-', 'deck-workspace-')) and root == roots[0]:
                desktop.mkdir(parents=True, exist_ok=True)
                target = desktop / name
                if target.is_symlink():
                    raise ValueError(f'Refusing to overwrite symlink: {target}')
                if not target.is_file() or target.read_text() != new:
                    target.write_text(new)
                target.chmod(0o755)
    print('Desktop icons reconciled; Gaming Mode artwork remains owned by SteamGridDB.')
    return 0


def status():
    missing = []
    for icon in sorted(ICONS):
        path = icon_path(icon)
        source = core.ROOT / 'modules/base/icons' / f'{icon}.svg'
        if not path.is_file() or path.read_bytes() != source.read_bytes():
            missing.append(str(path))
    for root in {Path.home() / '.local/share/applications', Path.home() / 'Desktop/Deck-Setup-Staged', Path.home() / 'Desktop', desktop_dir()}:
        for name, icon in ENTRIES.items():
            path = root / name
            if path.is_file() and (f'Icon={icon_path(icon)}' not in path.read_text().splitlines() or not os.access(path, os.X_OK)):
                missing.append(str(path))
    for path in missing:
        print('NEEDS REPAIR: ' + path)
    print('Desktop icons: ' + ('READY' if not missing else 'run deckctl desktop apply'))
    return 2 if missing else 0

def exec_line(arguments):
    """Encode literal argv using Desktop Entry escaping, without shell parsing."""
    encoded=[]
    for argument in arguments:
        value=str(argument)
        if any(c in value for c in ('\n','\r','\x00')): raise ValueError('Invalid desktop argument')
        value=value.replace('%','%%')
        # Desktop string unescaping precedes Exec argument unquoting.
        value=value.replace('\\', '\\\\\\\\').replace('"', '\\\\"').replace('`','\\\\`').replace('$','\\\\$')
        encoded.append('"'+value+'"')
    return ' '.join(encoded)
