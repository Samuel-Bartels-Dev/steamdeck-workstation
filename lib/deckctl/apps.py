"""Selectable desktop Flatpaks; removal preserves app data and other scopes."""
from __future__ import annotations
import json
import subprocess
import sys
from . import core


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
            return subprocess.run(['flatpak', 'update', '--user', '-y', app_id]).returncode
        return 0
    if action == 'verify':
        return 1
    return subprocess.run(['flatpak', 'install', '--user', '-y', 'flathub', app_id]).returncode


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
            rows = [{**app, 'key': key, 'selected': key in selected, 'installed': has(app['id'])}
                    for key, app in apps.items()]
            if args.json:
                print(json.dumps(rows, indent=2))
            else:
                for row in rows:
                    print(f"{row['key']:<10} {'selected' if row['selected'] else 'skipped':<9} "
                          f"{'installed' if row['installed'] else 'absent':<10} {row['name']}")
            return 0
        names = known(args.names) if args.names else selected
        if args.names:
            save(selected + names)
        failed = False
        for key in names:
            if module_action('install', apps[key]['id']):
                failed = True
        return 1 if failed else 0
    except (ValueError, OSError, EOFError, KeyboardInterrupt) as exc:
        print(f'Apps: {exc or "selection cancelled; choices were not saved"}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    try:
        if len(sys.argv) != 3 or sys.argv[1] not in ('install', 'verify'):
            raise ValueError('Expected install/verify and a registered Flatpak ID')
        raise SystemExit(module_action(sys.argv[1], sys.argv[2]))
    except (ValueError, OSError) as exc:
        print(f'Apps: {exc}', file=sys.stderr)
        raise SystemExit(1)
