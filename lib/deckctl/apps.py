"""Selectable desktop Flatpaks; removal preserves app data and other scopes."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path
from . import core

GAMING_KEYS = frozenset(('discord', 'parsec', 'spotify', 'slack'))


def gaming_desktop(key):
    return Path.home()/'.local/share/applications'/('deck-app-'+key+'.desktop')


def gaming_status(key):
    if key not in GAMING_KEYS:
        return None
    from . import app_shortcuts
    return app_shortcuts.status('app:'+key, catalog()[key]['name'], gaming_desktop(key))


def ensure_gaming_shortcut(key):
    if key not in GAMING_KEYS:
        return None
    from . import app_shortcuts
    app = catalog()[key]
    if not has(app['id']):
        raise RuntimeError(app['name']+' is not installed; no Steam shortcut was submitted.')
    path = gaming_desktop(key)
    text = ('[Desktop Entry]\nType=Application\nName='+app['name']+'\n'
            'Exec=/usr/bin/flatpak run '+app['id']+'\nIcon='+app['id']+'\n'
            'Terminal=false\nCategories=Network;\n')
    if path.is_symlink() or (path.exists() and path.read_text() != text):
        raise RuntimeError(app['name']+' managed launcher was edited; it was preserved. Review it before Retry.')
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open('x') as stream:
            stream.write(text)
        path.chmod(0o755)
    state = app_shortcuts.ensure('app:'+key, app['name'], path)
    print(app['name']+' Gaming Mode: '+state)
    return state


def catalog():
    return json.loads((core.ROOT / 'config/desktop-apps.json').read_text())


def selection():
    apps = catalog()
    path = core.CONFIG_HOME / 'apps.json'
    if not path.exists():
        return list(apps)
    data = json.loads(path.read_text())
    selected = data.get('selected') if isinstance(data, dict) else None
    if (not isinstance(selected, list) or any(not isinstance(k, str) or k not in apps for k in selected)
            or len(selected) != len(set(selected))):
        raise ValueError(f'Invalid app selection: {path}; repair it before installing apps.')
    return selected


def save(selected):
    core.save_json(core.CONFIG_HOME / 'apps.json', {'selected': sorted(set(selected))})


def known(names):
    apps = catalog()
    for name in names:
        if name not in apps:
            raise ValueError(f'Unknown app: {name}. Run deckctl apps list.')
    return list(dict.fromkeys(names))


def has(app_id, scope=None):
    args = ['flatpak', 'info'] + ([scope] if scope else []) + [app_id]
    return subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def module_action(action, app_id):
    apps = catalog()
    key = next((k for k, app in apps.items() if app['id'] == app_id), None)
    if key is None:
        raise ValueError(f'Unregistered desktop app: {app_id}')
    if key not in selection():
        if action == 'install':
            print(f'[skip] {key} is not selected')
        return 0
    if has(app_id):
        if action == 'install' and has(app_id, '--user'):
            # Flatpak compares repository commits and downloads only updates.
            rc = subprocess.run(['flatpak', 'update', '--user', '-y', app_id]).returncode
            if rc: return rc
        if action == 'install': ensure_gaming_shortcut(key)
        return 0
    if action == 'verify':
        return 1
    rc = subprocess.run(['flatpak', 'install', '--user', '-y', 'flathub', app_id]).returncode
    if not rc: ensure_gaming_shortcut(key)
    return rc


def choose(names, none=False):
    selected = selection()
    if names and none:
        raise ValueError('Use app names or --none, not both.')
    if names:
        selected = known(names)
    elif none:
        selected = []
    else:
        if not sys.stdin.isatty():
            raise ValueError('Provide app names or --none in noninteractive sessions.')
        print('Choose desktop apps for future installs. No apps will be removed.')
        for key, app in catalog().items():
            default = key in selected
            answer = input(f"{app['name']}? [{'Y/n' if default else 'y/N'}] ").strip().lower()
            while answer not in ('', 'y', 'yes', 'n', 'no'):
                answer = input('Enter y or n: ').strip().lower()
            enabled = default if not answer else answer in ('y', 'yes')
            if enabled and key not in selected:
                selected.append(key)
            elif not enabled and key in selected:
                selected.remove(key)
    save(selected)
    print('Selected: ' + (', '.join(selected) or 'none'))
    print('Run deckctl apps install to install these apps. Existing apps are kept.')
    return 0


def uninstall(names, yes=False):
    names = known(names)  # Validate every target before any mutation.
    selected = selection()
    apps = catalog()
    targets = []
    for key in names:
        app_id = apps[key]['id']
        present = has(app_id, '--user')
        if not present and has(app_id):
            raise ValueError(f'{key} is installed outside the user scope; no changes made.')
        targets.append((key, app_id, present))
        print(f'{key}: {"remove user app" if present else "already absent"}; keep settings; deselect for future installs')
    if not yes:
        print('Preview only. Repeat with --yes to apply. Close the selected apps first.')
        return 0
    # Persist intent first: an interrupted/failed removal must not trigger a reinstall.
    save([key for key in selected if key not in names])
    failed = False
    for key, app_id, present in targets:
        if present:
            result = subprocess.run(['flatpak', 'uninstall', '--user', '--app', '--no-related', '-y', app_id])
            if result.returncode or has(app_id, '--user'):
                print(f'{key}: removal failed; selection is disabled; retry this uninstall.', file=sys.stderr)
                failed = True
    return 1 if failed else 0


def add_parser(subparsers):
    parser = subparsers.add_parser('apps', help='Choose, install or safely remove desktop apps')
    sp = parser.add_subparsers(dest='apps_command', required=True)
    ls = sp.add_parser('list'); ls.add_argument('--json', action='store_true')
    sel = sp.add_parser('select'); sel.add_argument('names', nargs='*', help='App keys replacing the selection; omit for the interactive chooser.'); sel.add_argument('--none', action='store_true', help='Select no desktop apps; keep existing installations.')
    ins = sp.add_parser('install'); ins.add_argument('names', nargs='*', help='App keys to enable and install; omit for the saved selection.')
    un = sp.add_parser('uninstall'); un.add_argument('names', nargs='+', help='Exact app keys to remove from the user installation.'); un.add_argument('--yes', action='store_true')


def dispatch(args):
    try:
        if args.apps_command == 'select':
            return choose(args.names, args.none)
        if args.apps_command == 'uninstall':
            return uninstall(args.names, args.yes)
        apps = catalog()
        selected = selection()
        if args.apps_command == 'list':
            rows = [{**app, 'key': key, 'selected': key in selected, 'installed': has(app['id']), 'gamingMode': gaming_status(key)}
                    for key, app in apps.items()]
            if args.json:
                print(json.dumps(rows, indent=2))
            else:
                for row in rows:
                    print(f"{row['key']:<10} {'selected' if row['selected'] else 'skipped':<9} "
                          f"{'installed' if row['installed'] else 'absent':<10} {row['name']}"+
                          (f" — Gaming Mode {row['gamingMode']}" if row['gamingMode'] else ''))
            return 0
        names = known(args.names) if args.names else selected
        if args.names:
            save(selected + names)
        failed = False
        for key in names:
            try:
                if module_action('install', apps[key]['id']): failed = True
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                print(f"{apps[key]['name']}: {exc}", file=sys.stderr)
                failed = True
        return 1 if failed else 0
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError, EOFError, KeyboardInterrupt) as exc:
        print(f'Apps: {exc or "selection cancelled; choices were not saved"}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    try:
        if len(sys.argv) != 3 or sys.argv[1] not in ('install', 'verify'):
            raise ValueError('Expected install/verify and a registered Flatpak ID')
        raise SystemExit(module_action(sys.argv[1], sys.argv[2]))
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'Apps: {exc}', file=sys.stderr)
        raise SystemExit(1)
