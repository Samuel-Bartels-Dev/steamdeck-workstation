"""On-demand read-only catalog inventory, independent from desired selections."""
from collections import deque
import os
import subprocess
import threading
import time
from . import setup_plan


def catalog_rows(catalog):
    payload = {'modules': catalog['defaults'], 'apps': [r['id'] for r in catalog['apps']],
               'components': {group:[r['id'] for r in rows] for group,rows in catalog['components'].items()},
               'launchers':[r['id'] for r in catalog['launchers']],
               'plugins':[r['id'] for r in catalog['plugins']], 'css':[r['id'] for r in catalog['css']],
               'palette':catalog['palette'], 'appearance':catalog['appearance']}
    return [r for r in setup_plan.items(payload)[1] if r['visible']]


def local(row):
    if 'flatpak' in row:
        probe = subprocess.run(['flatpak','info','--show-commit',row['flatpak']], text=True,
                               capture_output=True, timeout=8, env=dict(os.environ, LC_ALL='C'))
        if probe.returncode and 'not installed' not in probe.stderr.lower():
            raise RuntimeError('Flatpak inventory unavailable')
        installed, evidence = bool(probe.returncode == 0 and probe.stdout.strip()), {}
    else:
        installed, evidence = setup_plan.present(row)
    state = evidence.get('status')
    if installed and evidence.get('configured') is False:
        label = 'Installed · needs setup'; status = 'NEEDS_SETUP'
    elif installed:
        label = 'Installed'; status = 'INSTALLED'
    elif state in ('CONFIG_REQUIRED','DEGRADED','API_READY','TEST_REQUIRED','STOPPED_OR_UNREACHABLE','TEST_FAILED','NOT_CONFIGURED') or evidence.get('configuration'):
        label = 'Needs setup'; status = 'NEEDS_SETUP'
    elif state == 'FAILED':
        label = 'Needs attention'; status = 'FAILED'
    else:
        label = 'Not installed'; status = 'MISSING'
    return {'key':row['key'], 'name':row.get('name',row['key']), 'label':label, 'status':status, 'installed':installed,
            'note':evidence.get('message',''), 'checkedAt':time.time()}


def remote(row, current):
    details = setup_plan.inspect(row, online=True)
    if not details['installed']: return local(row)
    action = details['action']; check = details['updateCheck']
    if action == 'CONFIGURE': return current
    if action == 'UPDATE': label, status = 'Update available', 'UPDATE'
    elif action == 'UP_TO_DATE': label, status = 'Up to date', 'CURRENT'
    elif action == 'PRESERVE_SYSTEM': label, status = 'Installed · system managed', 'INSTALLED'
    elif 'Unavailable' in check or 'unavailable' in check:
        label, status = 'Installed · couldn’t check updates', 'UNKNOWN'
    else: label, status = 'Installed · update status unknown', 'INSTALLED'
    return {**current, 'label':label, 'status':status, 'note':check,
            'installedVersion':details.get('installedVersion'), 'availableVersion':details.get('availableVersion'),
            'checkedAt':time.time()}


class Scan:
    def __init__(self, rows):
        self.rows = deque(rows)
        self.guard = threading.Lock()
        self.stopped = threading.Event()
        self.results = {}
        self.total = len(rows)
        self.completed = 0
        for _ in range(min(4,len(rows))): threading.Thread(target=self.work, daemon=True).start()

    def work(self):
        while not self.stopped.is_set():
            with self.guard:
                if not self.rows: return
                row = self.rows.popleft()
            result = None
            try:
                result = local(row)
                with self.guard: self.results[row['key']] = result
                if result['installed'] and not self.stopped.is_set(): result = remote(row, result)
            except Exception:
                # One unavailable provider must not prevent the rest of the catalog scan.
                result = {**(result or {}), 'key':row['key'], 'name':row.get('name',row['key']),
                          'label':'Installed · couldn’t check updates' if result and result.get('installed') else 'Couldn’t check', 'status':'UNKNOWN',
                          'note':'Provider unavailable or timed out. Check connectivity and refresh to retry.', 'checkedAt':time.time()}
            with self.guard:
                self.results[row['key']] = result
                self.completed += 1

    def snapshot(self):
        with self.guard:
            return {'items':dict(self.results), 'running':self.completed < self.total and not self.stopped.is_set(),
                    'completed':self.completed, 'total':self.total}

    def close(self): self.stopped.set()
