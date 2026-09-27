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
    followup = row.get('followup', '')
    if installed and followup and evidence.get('configured') is False:
        label = {'signin':'Needs sign-in', 'pairing':'Needs pairing', 'setup':'Needs setup'}.get(followup, 'Needs setup')
        status = 'NEEDS_SETUP'
    elif installed:
        label = 'Installed'; status = 'INSTALLED'
    elif followup and state in ('CONFIG_REQUIRED','DEGRADED','API_READY','TEST_REQUIRED','STOPPED_OR_UNREACHABLE','TEST_FAILED','NOT_CONFIGURED'):
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
    elif check == 'Existing unmanaged tool; preserved':
        label, status = 'Installed · managed elsewhere', 'INSTALLED'
    elif check == 'Version comparison unavailable':
        label, status = 'Installed · versions not comparable', 'INSTALLED'
    elif 'Unavailable' in check or 'unavailable' in check:
        label, status = 'Installed · couldn’t check updates', 'UNKNOWN'
    else: label, status = 'Installed · update checking unavailable', 'INSTALLED'
    notes = {
        'Not checked': ('This component has no automatic update checker. Installed state was checked; update availability was not.', 'Use the component’s own update controls. Refresh status rechecks installed state.'),
        'Existing unmanaged tool; preserved': ('This tool was installed outside the workstation’s managed installer; its version is preserved.', 'Update through the tool’s original installer or package manager.'),
        'Version comparison unavailable': ('Release metadata was retrieved, but its version could not be compared reliably with the installed version.', 'Compare the installed and available versions before updating.'),
        'System installation is reused; update through its owner': ('This installation is managed by the system rather than this installer.', 'Use Discover or the installation’s original package manager to check updates.'),
        'Unavailable; installer will check': ('The provider did not return usable update metadata. This does not mean an update is needed.', 'Check connectivity and use Refresh status to retry. Other components can still be installed.'),
    }
    note, next_action = notes.get(check, (check, ''))
    return {**current, 'label':label, 'status':status, 'note':details.get('updateReason') or note,
            'nextAction':details.get('updateNextAction') or next_action,
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
            except Exception as exc:
                # One unavailable provider must not prevent the rest of the catalog scan.
                result = {**(result or {}), 'key':row['key'], 'name':row.get('name',row['key']),
                          'label':'Installed · couldn’t check updates' if result and result.get('installed') else 'Couldn’t check', 'status':'UNKNOWN',
                          'note':('The installed-state check failed.' if result is None else 'The update check failed; the installed component is still detected.') + (' The provider timed out.' if isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)) else ' The provider or local checker was unavailable.'),
                          'nextAction':'Check connectivity and use Refresh status to retry. Other components can still be installed.', 'checkedAt':time.time()}
            with self.guard:
                self.results[row['key']] = result
                self.completed += 1

    def snapshot(self):
        with self.guard:
            return {'items':dict(self.results), 'running':self.completed < self.total and not self.stopped.is_set(),
                    'completed':self.completed, 'total':self.total}

    def close(self): self.stopped.set()
