"""Durable per-item installer. Runs on demand in Konsole; no startup service."""
from __future__ import annotations
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import time
from . import core, setup_plan


class NeedsSetup(RuntimeError):
    pass


def state_path(): return core.STATE/'setup-items.json'
def lock_path(): return core.STATE/'setup-items.lock'


def running():
    try:
        with lock_path().open('rb') as stream:
            try: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: return True
            fcntl.flock(stream, fcntl.LOCK_UN)
    except FileNotFoundError: pass
    return False


def snapshot():
    state = core.load_json(state_path(), {})
    live = running()
    state['running'] = live
    if not live:
        for row in state.get('items', {}).values():
            if row.get('status') == 'RUNNING':
                row.update(status='INTERRUPTED', message='Installation stopped before verification. Resume to retry this item.')
    return state


@contextmanager
def lock():
    core.STATE.mkdir(parents=True, exist_ok=True)
    with lock_path().open('a+b') as stream:
        try: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc: raise ValueError('An installation is already running') from exc
        try: yield
        finally: fcntl.flock(stream, fcntl.LOCK_UN)


def _run(args, env=None):
    result = subprocess.run(args, env=env)
    if result.returncode: raise RuntimeError('Installer exited with code '+str(result.returncode)+'. See Konsole for its explanation.')


def _flatpak(app_id):
    found = setup_plan.command(['flatpak', 'info', '--show-commit', app_id])
    if found:
        if setup_plan.command(['flatpak', 'info', '--user', '--show-commit', app_id]):
            _run(['flatpak', 'update', '--user', '-y', app_id])
        return
    _run(['flatpak', 'install', '--user', '-y', 'flathub', app_id])


def _module(mid):
    if mid == 'decky' and core._decky_loader_present(): return
    result = core.run_action(mid, 'install')
    if result is not None and result.returncode: raise RuntimeError('Module installer failed; see Konsole.')
    if mid == 'decky':
        if core._decky_loader_present(): return
        raise NeedsSetup('Open Decky Loader setup below, finish its installer, then resume your plugins.')
    checked = core.module_status(mid)
    if checked.get('status') not in ('READY', 'OPTIONAL'):
        raise NeedsSetup(checked.get('message') or 'Complete the provider setup, then resume.')


def execute(row):
    """Only catalog-owned commands may reach this dispatcher."""
    from . import terminal, ai_workspace, workspace, decky_installer, css_stack, containers, launchers
    key, name = row['key'], row.get('component')
    if 'flatpak' in row:
        _flatpak(row['flatpak']); return
    if row['kind'] == 'support': return
    if key == 'module:ai-workspace': ai_workspace.configure(); return
    if row['kind'] == 'module': _module(row['owner']); return
    if key.startswith('terminal:'):
        if terminal.apply(only=name): raise RuntimeError('Tool installation needs attention; see Konsole.')
        return
    if key in ('dev:codex', 'dev:claude-code'):
        script = 'install-codex.sh' if name == 'codex' else 'install-claude.sh'
        _run([str(core.ROOT/'modules/dev'/script)]); return
    if key == 'dev:docker':
        if containers.provision(): raise NeedsSetup('Docker prerequisites or container verification need attention.')
        return
    if key == 'dev:distrobox':
        if not shutil.which('distrobox') or not shutil.which('podman'): raise NeedsSetup('Distrobox and Podman must be available on this system.')
        dest = core.CONFIG_HOME/'distrobox.ini'; dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(core.ROOT/'modules/dev/distrobox.ini', dest)
        if not setup_plan.present(row)[0]: _run(['distrobox', 'assemble', 'create', '--file', str(dest)])
        return
    if key == 'ai-workspace:ollama':
        plan = ai_workspace.ollama_release_plan()
        if plan is not None:
            ai_workspace.check_space(runtime=True)
            ai_workspace.install_ollama(plan)
        return
    if key.startswith('ai-workspace:model'):
        model = next(model for model, data in ai_workspace.LOCAL_MODELS.items() if data['component'] == name)
        if ai_workspace.model_update_needed(model): ai_workspace.pull(model)
        return
    if key.startswith('workspace:'):
        if workspace.setup(only=name): raise RuntimeError('Web shortcut creation failed')
        return
    if key.startswith('media:'):
        if name == 'keeper': raise NeedsSetup('Open KeeperFill setup to approve the browser extension and sign in.')
        helper = Path.home()/'.local/share/deckctl/media'; helper.mkdir(parents=True, exist_ok=True)
        for source in ('services.json', 'setup-media.sh'): shutil.copy2(core.ROOT/'modules/media'/source, helper/source)
        _run(['bash', str(helper/'setup-media.sh'), '--all'], env=dict(os.environ, DECKCTL_CONFIG=str(core.CONFIG_HOME), DECKCTL_MEDIA_ITEM=name))
        return
    if key == 'remote:tailscale':
        _run([str(core.ROOT/'modules/remote/install-tailscale-steamos.sh')]); return
    if key == 'launcher:battlenet':
        if not launchers.battlenet_installed() and launchers.install_battlenet(): raise NeedsSetup('Complete Battle.net installation, then retry.')
        return
    if key == 'launcher:nonsteamlaunchers':
        dest = Path.home()/'Desktop/Deck-Setup-Staged/NonSteamLaunchers.desktop'; dest.parent.mkdir(parents=True, exist_ok=True)
        _run(['curl', '-fL', '--retry', '2', 'https://raw.githubusercontent.com/moraroy/NonSteamLaunchers-On-Steam-Deck/main/NonSteamLaunchers.desktop', '-o', str(dest)])
        dest.chmod(0o755); return
    if row['kind'] == 'plugin':
        if decky_installer.install_selected(only=name, assume_yes=True): raise NeedsSetup('Plugin needs attention in the Decky Plugin Store.')
        return
    if row['kind'] == 'css':
        if css_stack.apply(only=name): raise NeedsSetup('This CSS component needs attention; see Konsole.')
        return
    if row['kind'] == 'css-profile':
        if css_stack.apply(): raise NeedsSetup('CSS colors or recovery profile did not verify.')
        return
    raise ValueError('Unsupported install item: '+key)


def verify(row):
    if row['kind'] == 'support': return True
    if row['kind'] == 'css':
        from . import css_stack
        return css_stack.component_ready(row['component'])
    if row['key'] in ('terminal:shell', 'terminal:konsole'):
        from . import terminal
        state = terminal.status_data()
        keys = ('shell_config',) if row['component'] == 'shell' else ('konsole_profile', 'konsole_scheme', 'konsole_default')
        return all(state.get(key) for key in keys)
    return setup_plan.present(row)[0]


def run(only=None, resume=False):
    plan, rows = setup_plan.items()
    by_key = {row['key']: row for row in rows}
    if only is not None and only not in by_key: raise ValueError('Item is not selected in the saved plan')
    wanted = set(by_key)
    if only is not None:
        wanted = set()
        def include(key):
            if key in wanted: return
            wanted.add(key)
            for parent in by_key[key]['requires']: include(parent)
        include(only)
    with lock():
        fingerprint = setup_plan.fingerprint(plan)
        previous = core.load_json(state_path(), {})
        same = previous.get('fingerprint') == fingerprint
        state = {'fingerprint': fingerprint, 'version': (core.ROOT/'VERSION').read_text().strip(),
                 'startedAt': time.time(), 'items': previous.get('items', {}) if same else {}}
        records = state['items']
        for row in rows:
            records.setdefault(row['key'], {'name': row['name'], 'status': 'PENDING', 'message': ''})
        def record(key, status, message):
            records[key].update(status=status, message=message, updatedAt=time.time())
            core.save_json(state_path(), state)
        try:
            for row in rows:
                key = row['key']
                if key not in wanted: continue
                if (resume or only is not None) and records[key]['status'] == 'DONE' and verify(row): continue
                blockers = [parent for parent in row['requires'] if records.get(parent, {}).get('status') != 'DONE']
                if blockers:
                    record(key, 'BLOCKED', 'Finish '+', '.join(by_key[parent]['name'] for parent in blockers)+' first.'); continue
                record(key, 'RUNNING', 'Checking prerequisites and available space.')
                print('\n==> '+row['name'], flush=True)
                try:
                    path, budget, _ = setup_plan.storage_budget(row, False)
                    if budget is not None and not verify(row):
                        anchor = path.resolve()
                        while not anchor.exists(): anchor = anchor.parent
                        if shutil.disk_usage(anchor).free < budget + setup_plan.GIB:
                            raise RuntimeError('Not enough free space for this item’s staging allowance plus 1 GiB headroom.')
                    record(key, 'RUNNING', 'Installing this item; download and provider progress appear in Konsole.')
                    execute(row)
                    record(key, 'RUNNING', 'Verifying the installed result.')
                    if not verify(row): raise NeedsSetup('Installer finished, but this item still needs setup or verification.')
                    record(key, 'DONE', 'Installed and verified.')
                except NeedsSetup as exc: record(key, 'NEEDS_SETUP', str(exc))
                except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc: record(key, 'FAILED', str(exc))
        except (KeyboardInterrupt, EOFError):
            for key in wanted:
                if records[key]['status'] == 'RUNNING': record(key, 'INTERRUPTED', 'Interrupted; resume to retry this item.')
            print('\nProgress saved. Run deckctl setup install --resume.')
            return 2
        state['finishedAt'] = time.time()
        core.save_json(state_path(), state)
        failed = any(records[key]['status'] == 'FAILED' for key in wanted)
        pending = any(records[key]['status'] != 'DONE' for key in wanted)
        return 1 if failed else 2 if pending else 0
