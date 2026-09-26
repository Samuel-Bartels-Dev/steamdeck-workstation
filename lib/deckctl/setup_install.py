"""Durable per-item installer. Runs on demand; no startup service."""
from __future__ import annotations
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
_verbose = ContextVar('setup_verbose', default=False)
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import time
from . import core, setup_plan, install_log, install_progress, run_log, privilege, user_session


class NeedsSetup(RuntimeError):
    pass


def state_path(): return core.STATE/'setup-items.json'
def lock_path(): return core.STATE/'setup-items.lock'


def queue_control():
    raw = os.environ.get('DECKCTL_UI_CONTROL')
    if os.environ.get('DECKCTL_UI_RUN') != '1' or not raw: return {}
    path = Path(raw)
    if path.parent != core.STATE or not path.name.startswith('setup-control-') or path.is_symlink():
        raise ValueError('Invalid UI queue control path')
    return core.load_json(path, {})


def queue_checkpoint(state):
    while True:
        control = queue_control()
        if control.get('cancel'): raise KeyboardInterrupt()
        paused = bool(control.get('pause'))
        status = 'PAUSED' if paused else 'RUNNING'
        if state.get('queueStatus') != status:
            state['queueStatus'] = status
            core.save_json(state_path(), state)
        if not paused: return
        time.sleep(.2)


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
    if args and args[0] == 'flatpak':
        from .flatpak_progress import Reporter
        reporter = Reporter()
        run_log.run_step(args, dict(os.environ if env is None else env, LC_ALL='C'),
                         verbose=_verbose.get(), on_output=reporter)
        return reporter.last_phase
    result = subprocess.run(args, env=env)
    if result.returncode: raise RuntimeError('Installer exited with code '+str(result.returncode)+'. See the live output or item log for its explanation.')


def _flatpak(app_id):
    install_progress.report('Checking installation', 'Checking existing user and system installations.')
    found = setup_plan.command(['flatpak', 'info', '--show-commit', app_id])
    if found:
        if setup_plan.command(['flatpak', 'info', '--user', '--show-commit', app_id]):
            install_progress.report('Checking for updates', 'Already installed; checking for available updates.')
            phase = _run(['flatpak', 'update', '--user', '-y', app_id])
            return 'Already up to date; verified.' if phase == 'Up to date' else 'Updated and verified.' if phase == 'Updating' else 'Update check completed; verified.'
        else:
            install_progress.report('Using existing installation', 'System installation found; updates remain managed by its owner.')
        return 'Existing system installation reused and verified.'
    install_progress.report('Installing', 'Application is missing; installing the selected Flatpak.')
    _run(['flatpak', 'install', '--user', '-y', 'flathub', app_id])
    return 'Installed and verified.'


def _module(mid):
    if mid == 'decky' and core._decky_loader_present(): return
    result = core.run_action(mid, 'install')
    if result is not None and result.returncode: raise RuntimeError('Module installer failed; see the live output or item log.')
    if mid == 'decky':
        if core._decky_loader_present(): return
        raise NeedsSetup('Open Decky Loader setup below, finish its installer, then resume your plugins.')
    checked = core.module_status(mid)
    if checked.get('status') not in ('READY', 'OPTIONAL'):
        raise NeedsSetup(checked.get('message') or 'Complete the provider setup, then resume.')


def _nested_decky_change(row):
    return row.get('kind') in ('plugin', 'css', 'css-profile') and user_session.nested_desktop()


def execute(row):
    """Only catalog-owned commands may reach this dispatcher."""
    from . import terminal, ai_workspace, workspace, decky_installer, css_stack, containers, launchers
    key, name = row['key'], row.get('component')
    if _nested_decky_change(row):
        if verify(row): return 'Existing installation verified; no Decky restart requested.'
        raise NeedsSetup(user_session.NESTED_DESKTOP_NOTICE)
    if os.environ.get('DECKCTL_UI_RUN') == '1' and privilege.needed(row):
        if verify(row): return 'Existing installation verified.'
        privilege.command([])  # Refuse mutation without this runner's authorization.
    if os.environ.get('DECKCTL_UI_RUN') == '1' and interactive_provider(row):
        if verify(row):
            return setup_plan.present(row)[1].get('message') or 'Existing installation verified.'
        raise NeedsSetup('This provider needs interactive setup. Choose Continue in terminal for this item; other installations can continue here.')
    if 'flatpak' in row:
        return _flatpak(row['flatpak'])
    if row['kind'] == 'support': return
    if key == 'module:ai-workspace': ai_workspace.configure(); return
    if row['kind'] == 'module': _module(row['owner']); return
    if key.startswith('terminal:'):
        if terminal.apply(only=name): raise RuntimeError('Tool installation needs attention; see the live output or item log.')
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
        if name == 'keeper':
            if core._keeper_installed(): return 'Existing installation verified.'
            raise NeedsSetup('Install KeeperFill in Chrome, then retry. Sign-in and vault unlock stay in Chrome.')
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
        from . import downloads
        downloads.fetch('https://raw.githubusercontent.com/moraroy/NonSteamLaunchers-On-Steam-Deck/main/NonSteamLaunchers.desktop', dest, validate=downloads.desktop_entry)
        dest.chmod(0o755); return
    if row['kind'] == 'plugin':
        if decky_installer.install_selected(only=name, assume_yes=True): raise NeedsSetup('Plugin needs attention in the Decky Plugin Store.')
        return
    if row['kind'] == 'css':
        if css_stack.apply(only=name): raise NeedsSetup('This CSS component needs attention; see the live output or item log.')
        return
    if row['kind'] == 'css-profile':
        if css_stack.apply(): raise NeedsSetup('CSS colors or recovery profile did not verify.')
        return
    raise ValueError('Unsupported install item: '+key)


def interactive_provider(row):
    # Vendor wizards still need their interactive workflow. Decky/CSS use askpass.
    return (row['key'] in ('remote:tailscale','launcher:battlenet','dev:distrobox') or
            (row.get('kind') == 'module' and row['key'] not in ('module:base','module:ai-workspace','module:controller','module:hardware','module:library')))


def verify(row):
    if row['key'] == 'remote:tailscale':
        from . import tailscale
        return tailscale.status()['connected']
    if row['kind'] == 'support': return True
    if row['kind'] == 'css':
        from . import css_stack
        return css_stack.component_ready(row['component'])
    if row['key'] == 'terminal:konsole':
        from . import appearance
        if not appearance.enabled('konsole'): return True
    if row['key'] in ('terminal:shell', 'terminal:konsole'):
        from . import terminal
        state = terminal.status_data()
        keys = ('shell_config',) if row['component'] == 'shell' else ('konsole_profile', 'konsole_scheme', 'konsole_default')
        return all(state.get(key) for key in keys)
    return setup_plan.present(row)[0]


def run(only=None, resume=False, verbose=False):
    token = _verbose.set(verbose)
    try:
        with run_log.execution("install") as journal:
            code = _run_plan(only, resume, journal)
            journal.finish(code)
            return code
    finally: _verbose.reset(token)


def _run_plan(only, resume, journal):
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
    with lock(), privilege.Session() as permission:
        core.save_json(journal.path/'plan.json', {**core.load_json(journal.path/'plan.json', {}), 'plan': plan, 'items': rows, 'requested_item': only, 'resume': resume})
        fingerprint = setup_plan.fingerprint(plan)
        previous = core.load_json(state_path(), {})
        same = previous.get('fingerprint') == fingerprint
        state = {'run_id': journal.id, 'fingerprint': fingerprint, 'version': (core.ROOT/'VERSION').read_text().strip(),
                 'startedAt': time.time(), 'items': previous.get('items', {}) if same else {}}
        records = state['items']
        for row in rows:
            records.setdefault(row['key'], {'name': row['name'], 'status': 'PENDING', 'message': ''})
        def record(key, status, message):
            records[key].update(status=status, message=message, updatedAt=time.time())
            if status != 'RUNNING': records[key]['finishedAt'] = time.time()
            core.save_json(state_path(), state)
            if status != 'RUNNING':
                run_log.event(key, status, message, duration_ms=round((time.time()-records[key].get('startedAt', time.time()))*1000))
                print(f'[{key}] {status}: '+install_log.redact(message), flush=True)
        print(f'Run: {journal.id}\nDurable logs: {journal.path}', flush=True)
        try:
            admin_error = None
            admin_rows = [row for row in rows if row['key'] in wanted and
                          privilege.needed(row) and not _nested_decky_change(row)]
            if os.environ.get('DECKCTL_UI_RUN') == '1' and any(not verify(row) for row in admin_rows):
                state['queueStatus'] = 'AUTHENTICATING'
                core.save_json(state_path(), state)
                print('Administrator permission needed before installation. Complete the KDE password dialog; the password is not saved.', flush=True)
                try: permission.prepare()
                except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
                    admin_error = str(exc)
                    print(admin_error, flush=True)
            for row in rows:
                key = row['key']
                if key not in wanted: continue
                queue_checkpoint(state)
                if (resume or only is not None) and records[key]['status'] == 'DONE' and verify(row): continue
                if _nested_decky_change(row) and not verify(row):
                    record(key, 'NEEDS_SETUP', user_session.NESTED_DESKTOP_NOTICE); continue
                if admin_error and privilege.needed(row) and not verify(row):
                    record(key, 'NEEDS_SETUP', admin_error); continue
                blockers = [parent for parent in row['requires'] if records.get(parent, {}).get('status') != 'DONE']
                if blockers:
                    record(key, 'BLOCKED', 'Finish '+', '.join(by_key[parent]['name'] for parent in blockers)+' first.'); continue
                records[key].update(startedAt=time.time(), finishedAt=None, phase='Checking', downloaded=None, total=None)
                record(key, 'RUNNING', 'Checking prerequisites and available space.')
                print('\n['+key+'] Checking: '+row['name'], flush=True)
                run_log.event(key, 'RUNNING', 'Checking '+row['name'])
                def progress(phase, message, downloaded=None, total=None):
                    changed = records[key].get('phase') != phase
                    records[key].update(phase=phase, downloaded=downloaded, total=total)
                    record(key, 'RUNNING', message)
                    if changed:
                        print('['+key+'] '+phase+': '+install_log.redact(message), flush=True)
                        if os.environ.get('DECKCTL_UI_RUN') != '1': install_log.note(phase+': '+message)
                        run_log.event(key, 'RUNNING', phase+': '+message)
                try:
                    interactive = interactive_provider(row) and os.environ.get('DECKCTL_UI_RUN') != '1'
                    capture = nullcontext(None) if interactive else install_log.capture(key, stdout=os.environ.get('DECKCTL_UI_RUN') == '1')
                    with capture as log_path, install_progress.listen(progress):
                        records[key]['logPath'] = str(log_path) if log_path else None
                        path, budget, _ = setup_plan.storage_budget(row, False)
                        if budget is not None:
                            anchor = path.resolve()
                            while not anchor.exists(): anchor = anchor.parent
                            if shutil.disk_usage(anchor).free < budget + setup_plan.GIB:
                                raise RuntimeError('Not enough free space for this item’s staging allowance plus 1 GiB headroom.')
                        install_progress.report('Installing', 'Provider is running. Follow the live output for details.')
                        completion = execute(row)
                        install_progress.report('Verifying', 'Checking the installed result.')
                        if not verify(row): raise NeedsSetup('Installer finished, but this item still needs setup or verification.')
                        record(key, 'DONE', completion if isinstance(completion, str) else 'Installation verified.')
                except NeedsSetup as exc: record(key, 'NEEDS_SETUP', str(exc))
                except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
                    message = install_log.redact(str(exc))
                    if records[key].get('logPath'): message += ' Error log: '+records[key]['logPath']
                    record(key, 'FAILED', message)
                finally:
                    if records[key].get('logPath'): run_log.archive_item(key)
        except (KeyboardInterrupt, EOFError):
            state['queueStatus'] = 'CANCELLED' if queue_control().get('cancel') else 'INTERRUPTED'
            for key in wanted:
                if records[key]['status'] == 'RUNNING': record(key, 'INTERRUPTED', 'Interrupted; resume to retry this item.')
            print('\nProgress saved. Run deckctl setup install --resume.')
            core.save_json(state_path(), state)
            return 2
        state['finishedAt'] = time.time()
        state['queueStatus'] = 'FINISHED'
        core.save_json(state_path(), state)
        failed = any(records[key]['status'] == 'FAILED' for key in wanted)
        pending = any(records[key]['status'] != 'DONE' for key in wanted)
        return 1 if failed else 2 if pending else 0
