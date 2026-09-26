"""On-demand Qt Quick setup window using SteamOS's existing QML runtime."""
from __future__ import annotations
import json
from contextlib import contextmanager
import os
from pathlib import Path
import secrets
import select
import shutil
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from . import apps, core, setup_builder, gaming_options, css_stack, component_options, setup_plan, setup_install, setup_finish, reliability, appearance, install_log


APP_DESCRIPTIONS = {
    'flatseal': 'Manage permissions for your Flatpak apps',
    'zen': 'A dedicated desktop browser',
    'vscode': 'Code editing and development extensions',
    'zed': 'A focused code editor for your projects',
    'vlc': 'Play local video and audio files',
    'plex': 'Watch media from your Plex library',
    'spotify': 'Music and podcasts on your desktop',
    'discord': 'Chat and voice for your communities',
    'slack': 'Keep up with your team and workspaces',
}


@contextmanager
def renderer_diagnostics():
    """Drain renderer errors into a 16 KiB memory tail, never a growing temp file."""
    reader, writer = os.pipe()
    tail = bytearray()
    stop = threading.Event()
    def collect():
        try:
            while not stop.is_set():
                if not select.select([reader], [], [], .1)[0]: continue
                chunk = os.read(reader, 4096)
                if not chunk: break
                tail.extend(chunk)
                del tail[:-16384]
        finally: os.close(reader)
    thread = threading.Thread(target=collect, daemon=True)
    thread.start()
    try:
        with os.fdopen(writer, 'wb', buffering=0) as stream: yield stream, tail
    finally:
        thread.join(.5)
        stop.set()
        thread.join(.2)


class Session:
    def __init__(self, plan_only=False):
        self.plan_only = plan_only
        self.action_lock = threading.Lock()
        self.progress_lock = threading.Lock()
        self.progress_cache = {}
        self.process = None
        self.operation = None
        self.selected = None
        self.preview_result = {}
        self.preview_thread = None
        self.import_archive = None
        self.inventory_scan = None
        from .setup_activity import Sampler
        self.activity = Sampler()

    def snapshot(self):
        manifests = core.module_manifests()
        data = {'groups': setup_builder.catalog()['groups'],
                'apps': [{'id': key, 'name': app['name'], 'summary': APP_DESCRIPTIONS.get(key, 'Optional desktop app'),
                          'module': app['module']} for key, app in apps.catalog().items()],
                'modules': core.enabled_modules(), 'selectedApps': apps.selection(),
                'hasSavedPlan': (core.CONFIG_HOME/'modules.json').is_file(),
                'defaults': list(manifests),
                'components': component_options.catalog(), 'selectedComponents': component_options.selection(),
                'defaultComponents': component_options.defaults(),
                'launchers': [dict(item) for item in gaming_options.ITEMS], 'selectedLaunchers': gaming_options.selection(),
                'plugins': setup_builder.plugin_items(), 'selectedPlugins': sorted(core._decky_selected_folders()),
                'defaultPlugins': core._decky_default_selection(),
                'css': css_stack.selection_items(), 'selectedCss': css_stack.selection(),
                'defaultCss': [item['name'] for category in ('required','recommended') for item in css_stack._stack(unfiltered=True)[category]],
                'dependencies': {key: item[1].get('depends_on', []) for key, item in manifests.items()},
                'planOnly': self.plan_only,
                'runtimeVersion':(core.ROOT/'VERSION').read_text().strip(),
                'guideSeen':core.load_json(core.CONFIG_HOME/'setup-ui.json', {}).get('guide_seen', False),
                'palettes': css_stack.palette_catalog(),
                'cssPalette':css_stack.palette_status(),
                'palette': css_stack.palette_id(), 'appearance': appearance.selection(), 'appearanceTargets': appearance.TARGETS}
        descriptions = core.load_json(core.ROOT/'config/setup-copy.json', {})
        from . import preflight
        data['sudoReadiness'] = preflight.sudo_readiness()
        sections = dict(data)
        sections['modules'] = [item for group in data['groups'] for item in group['modules']]
        sections['components'] = [item for items in data['components'].values() for item in items]
        for section in ('modules', 'apps', 'components', 'launchers', 'plugins', 'css'):
            for item in sections[section]:
                item['summary'] = descriptions.get(section, {}).get(item['id'], item['summary'])
        catalogs = {
            'module': {item['id']: item for item in sections['modules']},
            'app': {item['id']: item for item in data['apps']},
            'launcher': {item['id']: item for item in data['launchers']},
        }
        data['layout'] = []
        seen = set()
        for section in core.load_json(core.ROOT/'config/setup-layout.json', []):
            items = []
            for reference in section['items']:
                kind, key = reference['kind'], reference['id']
                identity = (kind, reference.get('group'), key)
                if identity in seen:
                    raise ValueError('Duplicate setup choice: ' + key)
                seen.add(identity)
                catalog = ({item['id']: item for item in data['components'][reference['group']]}
                           if kind == 'component' else catalogs[kind])
                items.append({**catalog[key], **reference})
            data['layout'].append({**section, 'items': items})
        return data

    def inventory(self, refresh=False):
        from . import setup_inventory
        if refresh and (self.inventory_scan is None or not self.inventory_scan.snapshot()['running']):
            self.inventory_scan = setup_inventory.Scan(setup_inventory.catalog_rows(self.snapshot()))
        return self.inventory_scan.snapshot() if self.inventory_scan else {'items':{}, 'running':False, 'completed':0, 'total':0}

    def save(self, payload):
        if setup_install.running() or (self.process and self.process.poll() is None):
            raise ValueError('Wait for the current operation to finish before changing your plan.')
        roots = payload.get('modules')
        selected = payload.get('apps')
        known = core.module_manifests()
        if (not isinstance(roots, list) or not isinstance(selected, list)
                or any(not isinstance(x, str) or x not in known for x in roots)
                or any(not isinstance(x, str) or x not in apps.catalog() for x in selected)):
            raise ValueError('Invalid feature or app selection. Reopen setup and try again.')
        normalized = setup_builder._app_module_roots(roots, selected)
        setup_builder.save_plan(normalized, selected, payload.get("launchers"), payload.get("plugins"), payload.get("css"), payload.get("components"), payload.get("palette"), payload.get("appearance"))
        self.selected = core.topo(core.enabled_modules())
        self.process = None
        self.operation = None
        return {'saved': True, 'modules': self.selected}

    def share(self, operation):
        if setup_install.running() or (self.process and self.process.poll() is None):
            raise ValueError('Finish the current operation before sharing or replacing choices.')
        if operation == 'import-confirm':
            if not self.import_archive: raise ValueError('Choose a setup archive first.')
            archive, digest = self.import_archive
            import hashlib
            if hashlib.sha256(Path(archive).read_bytes()).hexdigest() != digest:
                raise ValueError('Archive changed since preview. Choose it again.')
            reliability.profile_import(archive)
            self.import_archive = None
            self.selected = core.topo(core.enabled_modules())
            self.process = None
            self.operation = None
            return {'imported': True}
        if operation == 'import-cancel':
            self.import_archive = None
            return {'cancelled': True}
        if operation not in ('export', 'import'): raise ValueError('Unknown sharing action.')
        dialog = shutil.which('kdialog')
        if not dialog: raise ValueError('KDE file picker is unavailable. Use deckctl profile export/import in Konsole.')
        args = ['--getsavefilename', str(Path.home()/'deck-setup.zip'), '*.zip'] if operation == 'export' else ['--getopenfilename', str(Path.home()), '*.zip']
        chosen = subprocess.run([dialog, *args], capture_output=True, text=True)
        if chosen.returncode or not chosen.stdout.strip(): return {'cancelled': True}
        path = chosen.stdout.strip()
        if operation == 'export':
            if Path(path).exists():
                confirm = subprocess.run([dialog, '--yesno', 'Replace the existing setup archive?'])
                if confirm.returncode: return {'cancelled': True}
            return {'exported': str(reliability.profile_export(path))}
        import hashlib
        digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        preview = reliability.profile_import(path, preview=True)
        self.import_archive = (path, digest)
        return preview

    def preview(self, payload):
        plan = setup_plan.normalize(payload)
        if self.preview_thread and self.preview_thread.is_alive():
            raise ValueError('A preview is already being checked. Please wait.')
        self.preview_result = {'running': True}
        def check():
            try:
                self.preview_result = {**setup_plan.preview(plan, online=True), 'running': False}
            except (ValueError, OSError, RuntimeError, KeyError, TypeError, AttributeError) as exc:
                self.preview_result = {'running': False, 'error': str(exc)}
        self.preview_thread = threading.Thread(target=check, daemon=True)
        self.preview_thread.start()
        return self.preview_result

    def start(self, operation, item=None):
        if self.plan_only:
            raise ValueError('Continue installation in the installer after saving this plan.')
        if not self.selected:
            if not (core.CONFIG_HOME/'modules.json').is_file():
                raise ValueError('Review and save a plan first.')
            self.selected = core.topo(core.enabled_modules())
        if setup_install.running() or (self.process and self.process.poll() is None):
            raise ValueError('An operation is already running.')
        commands = {'install': ['setup', 'install'], 'resume': ['setup', 'install', '--resume']}
        if operation == 'docker':
            if 'dev:docker' not in {row['key'] for row in setup_plan.items()[1]}:
                raise ValueError('Select Docker in your plan first.')
            commands[operation] = ['setup', 'install', '--item', 'dev:docker']
        if operation in ('retry', 'interactive'):
            if item not in {row['key'] for row in setup_plan.items()[1]}:
                raise ValueError('Item is not selected in the saved plan')
            commands[operation] = ['setup', 'install', '--item', item]
        if operation not in commands:
            raise ValueError('Unknown setup operation.')
        command = [str(core.ROOT/'bin/deckctl'), *commands[operation]]
        if operation in ('install','resume','retry','docker'):
            from . import setup_process, setup_activity
            self.activity = setup_activity.Sampler()
            self.process = setup_process.start([*command, '--verbose'], setup_plan.fingerprint(setup_plan.items()[0]))
        else:
            terminal = shutil.which('konsole')
            if not terminal: raise ValueError('Konsole is required for this interactive action.')
            env = dict(os.environ); env.pop('DECKCTL_UI_RUN', None)
            self.process = subprocess.Popen([terminal, '--separate', '--nofork', '-e', *command], env=env)
        self.operation = "install" if operation in ("resume", "retry", "interactive", "docker") else operation
        return self.progress()

    def console(self):
        from . import setup_process
        data = setup_process.snapshot(setup_plan.fingerprint(setup_plan.items()[0]))
        state = setup_install.snapshot()
        if data.get('finishedAt', float('inf')) < state.get('startedAt', 0): return {'text':''}
        from . import run_log
        run_id = state.get('run_id', '')
        if (not data.get('runId') and state.get('fingerprint') == setup_plan.fingerprint(setup_plan.items()[0])
                and state.get('startedAt', 0) >= data.get('startedAt', 0) and run_log.RUN_NAME.fullmatch(run_id)):
            data = {**data, 'runId':run_id, 'logDirectory':str(run_log.root()/run_id)}
        run_id = data.get('runId', '')
        if run_log.RUN_NAME.fullmatch(run_id):
            # One ordered whole-run record, never a concatenation of item logs.
            # The live capture remains until its archived copy is complete.
            key = 'run:'+run_id
            archive = run_log.root()/run_id/install_log.path_for(key).name
            for source in (install_log.path_for(key), archive):
                try:
                    run_log.safe(source)
                    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
                    with os.fdopen(fd, 'rb') as stream:
                        raw = stream.read(install_log.LIMIT+1)
                    if len(raw) > install_log.LIMIT: raise ValueError('Oversized combined run log')
                    text = install_log.redact(raw.decode('utf-8', errors='replace'))
                    return {**data, 'text':text, 'source':'run', 'sourceId':run_id,
                            'retainedLimit':install_log.LIMIT,
                            'historyTruncated':not text.startswith('Item: '+key+'\n'),
                            'logFile':str(archive), 'updatedAt':source.stat().st_mtime}
                except FileNotFoundError: continue
                except (OSError, ValueError) as exc:
                    return {**data, 'source':'unavailable', 'text':'', 'outputNotice':str(exc)}
        return {**data, 'source':'snapshot', 'sourceId':run_id or str(data.get('startedAt', '')),
                'retainedLimit':65536, 'historyTruncated':data.get('truncated', False),
                'outputNotice':'Live snapshot only; older whole-run output is unavailable.'}

    def control(self, action):
        if not self.process or not hasattr(self.process,'control'):
            raise ValueError('Controls are available only for the UI run started in this window.')
        self.process.control(action)
        return {**self.progress_cache, 'running':self.process.poll() is None,
                'operation':self.operation, 'controls':self.process.controls()}

    def log(self, item):
        if item not in {row['key'] for row in setup_plan.items()[1]}:
            raise ValueError('Unknown installation item')
        text = install_log.read(item)
        return {'item': item, 'text': text[-65536:], 'truncated': len(text) > 65536, 'logPath':str(install_log.path_for(item)),
                'updatedAt': install_log.path_for(item).stat().st_mtime}

    def github_limit(self):
        from . import run_log
        try:
            latest = next((row for row in run_log.runs() if row['operation'] == 'install'), None)
            if not latest: return None
            plan = run_log.read_json(Path(latest['directory'])/'plan.json')
            for check in plan.get('preflight', {}).get('checks', []):
                if check.get('name') == 'api.github.com' and check.get('rate_limited'):
                    reset = check.get('reset_at')
                    return {'resetAt':reset if type(reset) is int and reset > 0 else None, 'checkedAt':latest['started_at']}
        except (OSError, ValueError, TypeError, AttributeError): pass
        return None

    def progress(self):
        if not self.progress_lock.acquire(blocking=False):
            return self.progress_cache
        try:
            self.progress_cache = self._progress()
            return self.progress_cache
        finally:
            self.progress_lock.release()

    def _progress(self):
        state = setup_install.snapshot()
        plan, rows = setup_plan.items()
        matches = state.get('fingerprint') == setup_plan.fingerprint(plan)
        records = state.get('items', {}) if matches else {}
        live = state.get('running', False) or bool(self.process and self.process.poll() is None)
        visible = [{**row, **records.get(row['key'], {'status': 'PENDING', 'message': ''}), 'id': row['key']}
                   for row in rows if row['visible']]
        now = time.time()
        from . import setup_process
        console = setup_process.snapshot(setup_plan.fingerprint(plan))
        for row in visible:
            status = row.get('status')
            row['terminalRequired'] = setup_install.interactive_provider(row)
            row['resultLabel'] = ({'Installed and verified.':'Installed', 'Updated and verified.':'Updated',
                                   'Already up to date; verified.':'Already current',
                                   'Existing system installation reused and verified.':'Existing installation reused'}
                                  .get(row.get('message'), 'Verified')) if status == 'DONE' else {
                                      'FAILED':'Failed','INTERRUPTED':'Interrupted','NEEDS_SETUP':'Needs setup',
                                      'BLOCKED':'Waiting on dependency','PENDING':'Waiting','RUNNING':'In progress'}.get(status,status)
            row['nextAction'] = ('Open setup / sign-in and recheck readiness.' if row.get('followup') == 'signin' else
                                 'Pair your device and recheck readiness.' if row.get('followup') == 'pairing' else
                                 'Complete vendor setup and recheck readiness.' if row.get('followup') == 'setup' else
                                 'Use Recheck readiness to inspect the current installation.') if status == 'DONE' else {
                                     'FAILED':'Read Details, resolve the error, then retry this item.',
                                     'INTERRUPTED':'Resume to verify completed work and retry unfinished items.',
                                     'NEEDS_SETUP':'Complete the provider setup, then retry verification.',
                                     'BLOCKED':'Complete the required dependency first.'}.get(status,'')
            start = row.get('startedAt')
            end = now if row.get('status') == 'RUNNING' else row.get('finishedAt') or row.get('updatedAt', now)
            row['elapsedSeconds'] = max(0, int(end-start)) if isinstance(start, (float, int)) else 0
            path = install_log.path_for(row['key'])
            row['hasLog'] = not path.is_symlink() and path.is_file()
            activity = max(row.get('updatedAt') or start or now, path.stat().st_mtime if row['hasLog'] else 0,
                           console.get('lastOutputAt',0) if status == 'RUNNING' else 0)
            row['quietSeconds'] = max(0, int(now-activity))
            row['activityNotice'] = ('No new output for '+str(row['quietSeconds'])+
                                     's — possibly stalled or a quiet operation. Inspect output before cancelling; this is not a failure result.') if row.get('status') == 'RUNNING' and row['quietSeconds'] >= 90 else ''
        attention = {'FAILED', 'INTERRUPTED', 'NEEDS_SETUP', 'BLOCKED'}
        visible.sort(key=lambda row: 0 if row.get('status') == 'RUNNING' else 1 if row.get('status') in attention else 3 if row.get('status') == 'DONE' else 2)
        code = self.process.poll() if self.process else None
        operation = self.operation or ('install' if records else None)
        if not live and records and operation == 'install':
            complete = all(records.get(row['key'], {}).get('status') == 'DONE' for row in rows)
            if code is None or (code == 0 and not complete):
                code = 0 if complete else 2
        summary = {'total': len(visible), 'done': sum(row.get('status') == 'DONE' for row in visible),
                   'attention': sum(row.get('status') in attention for row in visible)}
        controls = self.process.controls() if self.process and hasattr(self.process,'controls') else {'available':False}
        failure = ''
        if not live and code not in (None, 0) and console.get('finishedAt', 0) >= state.get('startedAt', 0):
            failures = [line for line in console.get('text', '').splitlines() if line.startswith('FAIL ')]
            failure = '\n'.join(failures[-3:])
        from . import setup_activity
        active = next((row for row in visible if row.get('status') == 'RUNNING'), None)
        storage = setup_activity.storage_status(active)
        return {'running': live, 'operation': operation, 'summary': summary, 'failureMessage':failure,
                'network':setup_activity.network_status(), 'storage':storage,
                'githubLimit':self.github_limit(), 'cssPalette':css_stack.palette_status(),
                'controls':controls, 'queueStatus':state.get('queueStatus'),
                'activity':self.activity.sample() if live else self.activity.history,
                'exitCode': code, 'modules': visible, 'items': visible, 'resumable': bool(records) and not live,
                'hasHistory': bool(records), 'historyPlanChanged': bool(state.get('items')) and not matches,
                'unfinished': sum(records.get(row['key'],{}).get('status') != 'DONE' for row in rows) if records else 0,
                'lastRunAt': state.get('finishedAt') or state.get('startedAt')}


def launch(plan_only=False):
    runtime = shutil.which('qml6') or shutil.which('qml')
    if not runtime:
        raise ValueError('Qt Quick is unavailable. Run setup from an interactive terminal without DISPLAY for text mode.')
    session = Session(plan_only)
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, code, value):
            raw = json.dumps(value).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def handle_request(self, post=False):
            if (self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}'
                    or self.headers.get('Origin') or not self.path.startswith('/'+token+'/')):
                self.reply(403, {'error': 'Request refused'})
                return
            route = self.path.removeprefix('/'+token+'/')
            exclusive = post and route not in ('control', 'log', 'guide-seen')
            if exclusive and not session.action_lock.acquire(blocking=False):
                self.reply(409, {'error':'Another setup action is in progress. Please retry when it finishes.'})
                return
            try:
                if post:
                    size = int(self.headers.get('Content-Length', '0'))
                    if size < 1 or size > 16384:
                        raise ValueError('Invalid request size')
                    payload = json.loads(self.rfile.read(size))
                    if not isinstance(payload, dict):
                        raise ValueError('Expected an object')
                    if route == 'guide-seen':
                        core.save_json(core.CONFIG_HOME/'setup-ui.json', {'guide_seen':True})
                        result = {'saved':True}
                    elif route == 'inventory':
                        result = session.inventory(refresh=True)
                    elif route == 'save':
                        result = session.save(payload)
                    elif route == 'start':
                        result = session.start(payload.get('operation'), payload.get('item'))
                    elif route == 'control':
                        result = session.control(payload.get('action'))
                    elif route == 'preview':
                        result = session.preview(payload)
                    elif route == 'share':
                        result = session.share(payload.get('operation'))
                    elif route == 'log':
                        result = session.log(payload.get('item'))
                    elif route == 'finish':
                        result = setup_finish.action(payload.get('item'), payload.get('operation'))
                    else:
                        raise ValueError('Unknown operation')
                elif route == 'inventory':
                    result = session.inventory()
                elif route == 'sudo-readiness':
                    from . import preflight
                    result = preflight.sudo_readiness()
                elif route == 'catalog':
                    result = session.snapshot()
                elif route == 'finish':
                    result = {'items': setup_finish.rows()}
                elif route == 'preview':
                    result = session.preview_result
                elif route == 'progress':
                    result = session.progress()
                elif route == 'console':
                    result = session.console()
                else:
                    raise ValueError('Unknown view')
                self.reply(200, result)
            except (BrokenPipeError, ConnectionResetError):
                pass  # Closing the UI may abandon a pending read-only request.
            except (ValueError, OSError, RuntimeError, SystemExit) as exc:
                self.reply(400, {'error': str(exc)})
            finally:
                if exclusive: session.action_lock.release()

        def do_GET(self):
            self.handle_request()

        def do_POST(self):
            self.handle_request(True)

    with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            env = dict(os.environ, QT_QUICK_CONTROLS_STYLE='Basic')
            with renderer_diagnostics() as (diagnostic, tail):
                result = subprocess.call([runtime, str(core.ROOT/'lib/deckctl/ui/Setup.qml'), '--',
                                          f'http://127.0.0.1:{server.server_port}/{token}/'], env=env, stderr=diagnostic)
            if result:
                detail = install_log.redact(tail.decode(errors='replace').replace(token, '<session>'))
                raise ValueError('Qt Quick could not run. The GUI needs QtQuick, QtQuick.Controls, QtQuick.Layouts and QtQuick.Window imports plus a working Desktop Mode display. '
                                 'No system packages were changed. Use deckctl setup configure from a terminal if the GUI runtime is unavailable.\n'+detail[-4000:])
            return result or (2 if plan_only and session.selected is None else 0)
        finally:
            if session.process and hasattr(session.process, 'close'): session.process.close()
            if session.inventory_scan: session.inventory_scan.close()
            server.shutdown()
            thread.join()
