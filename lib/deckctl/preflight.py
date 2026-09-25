"""Read-only preflight using selected items and conservative existing space allowances."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from . import core, compatibility, setup_plan


def anchor(path):
    path = path.resolve()
    while not path.exists(): path = path.parent
    return path


def destination(path):
    target = anchor(path)
    stats = os.statvfs(target)
    writable = os.access(target, os.W_OK | os.X_OK) and not bool(stats.f_flag & os.ST_RDONLY)
    return {'path': str(path), 'existing_parent': str(target), 'device': target.stat().st_dev,
            'free_bytes': shutil.disk_usage(target).free, 'writable': writable,
            'status': 'PASS' if writable else 'FAIL',
            'note': 'Permission/mount flags checked without writing; not an offline filesystem integrity check.'}


def reserve():
    settings = core.settings()
    value = settings.get('storage_reserve_bytes', setup_plan.GIB)
    if type(value) is not int or value < setup_plan.GIB:
        raise ValueError('storage_reserve_bytes must be an integer of at least 1 GiB (existing safety floor)')
    return value


def network():
    # curl bounds DNS, TLS, connect and transfer time as one process; no unbounded getaddrinfo.
    rows = []
    endpoints = ('https://api.github.com', 'https://github.com', 'https://flathub.org/repo/flathub.flatpakrepo')
    for endpoint in endpoints:
        host = endpoint.split('/')[2]
        try:
            result = subprocess.run(['curl', '--head', '--fail', '--silent', '--show-error',
                                     '--proto', '=https', '--proto-redir', '=https', '--location', '--connect-timeout', '5', '--max-time', '12',
                                     endpoint], capture_output=True, text=True, timeout=15)
            passed = result.returncode == 0
        except (OSError, subprocess.TimeoutExpired): passed = False
        rows.append({'name': host, 'status': 'PASS' if passed else 'FAIL',
                     'message': 'HTTPS endpoint reachable' if passed else 'HTTPS probe failed; check DNS, network, proxy and TLS.'})
    return rows


def report(rows=None, online=False):
    if rows is None: _, rows = setup_plan.items()
    comp = compatibility.report()
    checks = []
    def add(name, status, message): checks.append({'name': name, 'status': status, 'message': message})
    host = comp['system']
    add('architecture', 'PASS' if host['architecture'] == 'x86_64' else 'FAIL', host['architecture'])
    add('SteamOS', 'PASS' if host['os'] == 'steamos' else 'WARN', 'Detected '+host['os']+' '+host['version'])
    add('hardware', 'WARN' if host['model'] == 'unknown' else 'PASS', host['model'])
    for name in ('flatpak', 'curl', 'tar', 'lsblk'):
        add(name, 'PASS' if shutil.which(name) else 'FAIL', 'Required executable '+name)
    add('sudo', 'PASS' if shutil.which('sudo') else 'WARN', 'Availability only; interactive authorization is provider-owned.')
    volumes = {}; unknown = []
    for row in rows:
        if row['kind'] == 'support': continue
        path, size, _ = setup_plan.storage_budget(row, False)
        info = destination(path)
        volume = volumes.setdefault(info['device'], {**info, 'required_bytes': reserve(), 'items': []})
        volume['items'].append(row['key'])
        volume['writable'] = volume['writable'] and info['writable']
        if size is None: unknown.append(row['key'])
        else: volume['required_bytes'] += size
    temp_info = destination(Path(tempfile.gettempdir()))
    if temp_info['device'] not in volumes and volumes:
        volumes[temp_info['device']] = {**temp_info, 'required_bytes': max(v['required_bytes'] for v in volumes.values()), 'items': ['temporary staging allowance']}
    for path in (core.STATE, core.CONFIG_HOME, Path(tempfile.gettempdir())):
        info = destination(path)
        add('writable:'+str(path), info['status'], info['note'])
    for volume in volumes.values():
        volume['status'] = 'PASS' if volume['writable'] and volume['free_bytes'] >= volume['required_bytes'] else 'FAIL'
        add('storage:'+volume['path'], volume['status'], 'Conservative known staging allowances plus reserve; unknown payloads excluded.')
    if unknown: add('unknown sizes', 'WARN', 'Provider must check additional space for: '+', '.join(unknown))
    for row in comp['components']:
        add('compatibility:'+row['component'], 'FAIL' if row['status'] == 'UNSUPPORTED' else 'WARN' if row['status'] == 'UNKNOWN' else 'PASS', row['status'])
    for row in storage_report():
        add('device:'+row['name'], row['status'], row.get('message', row.get('note', '')))
    if online: checks.extend(network())
    else: add('network', 'WARN', 'Not probed; run deckctl preflight --online before downloads.')
    status = 'FAIL' if any(c['status'] == 'FAIL' for c in checks) else 'WARN' if any(c['status'] == 'WARN' for c in checks) else 'PASS'
    return {'schema_version': 1, 'status': status, 'checks': checks, 'volumes': list(volumes.values()),
            'unknown_sizes': unknown, 'compatibility': comp, 'reserve_bytes': reserve()}


def command(as_json=False, online=False):
    data = report(online=online)
    if as_json: print(json.dumps(data, indent=2))
    else:
        for row in data['checks']: print(f"{row['status']:<5} {row['name']}: {row['message']}")
        print('RESULT '+data['status'])
    return 1 if data['status'] == 'FAIL' else 2 if data['status'] == 'WARN' else 0


def storage_report():
    """Validate optional role-card identity and actual mount flags, never mount/repair."""
    result = [{'name': 'Internal/home', **destination(Path.home())}]
    configured = core.settings().get('storage_devices', {})
    if not isinstance(configured, dict): raise ValueError('storage_devices must be an object')
    defaults = core.load_json(core.ROOT/'config/default.json', {}).get('storage', {})
    devices = list(core.walk_blocks(core.storage_devices()))
    for role, label in (('pc_games', defaults.get('games_label', 'DECK-GAMES')),
                        ('emulation', defaults.get('emu_label', 'DECK-EMU'))):
        expected = configured.get(role, {})
        if not isinstance(expected, dict): raise ValueError('Invalid storage device expectations')
        label = expected.get('label', label)
        matches = [d for d in devices if d.get('label') == label]
        row = {'name': label, 'role': role, 'status': 'WARN', 'message': 'Optional card not present'}
        if len(matches) > 1: row.update(status='FAIL', message='Duplicate labels; cannot identify intended card')
        elif matches:
            device = matches[0]
            mounts = [p for p in device.get('mountpoints', []) if p]
            row.update(uuid=device.get('uuid'), filesystem=device.get('fstype'), mounts=mounts)
            if expected.get('uuid') and expected['uuid'] != device.get('uuid'):
                row.update(status='FAIL', message='Wrong UUID; intended card is not mounted')
            elif not mounts: row.update(message='Card detected but not mounted')
            elif len(mounts) != 1: row.update(status='FAIL', message='Ambiguous mount targets')
            elif expected.get('mount') and expected['mount'] != mounts[0]:
                row.update(status='FAIL', message='Unexpected mount target')
            elif expected.get('filesystem') and expected['filesystem'] != device.get('fstype'):
                row.update(status='FAIL', message='Unexpected filesystem')
            elif not Path(mounts[0]).is_mount(): row.update(status='FAIL', message='Reported target is not an actual mount point')
            else:
                row.update(destination(Path(mounts[0])))
                row['message'] = 'Mounted; identity and permission checks only, not fsck or media health.'
        if expected.get('required') and row['status'] == 'WARN': row['status'] = 'FAIL'
        result.append(row)
    return result


def storage_command(as_json=False):
    data = storage_report()
    if as_json: print(json.dumps(data, indent=2))
    else:
        for row in data: print(row['name'], row['status'], row.get('message', row.get('note', '')), 'free='+str(row.get('free_bytes', 'unknown')))
    return 1 if any(r['status'] == 'FAIL' for r in data) else 2 if any(r['status'] == 'WARN' for r in data) else 0
