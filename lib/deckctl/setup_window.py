"""On-demand Qt Quick setup window using SteamOS's existing QML runtime."""
from __future__ import annotations
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
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


class Session:
    def __init__(self, plan_only=False):
        self.plan_only = plan_only
        self.process = None
        self.operation = None
        self.selected = None
        self.preview_result = {}
        self.preview_thread = None
        self.import_archive = None
        self.inventory_scan = None

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
                'palettes': css_stack.palette_catalog(),
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
        terminal = shutil.which('konsole')
        if not terminal:
            raise ValueError('Konsole is required for interactive installer prompts.')
        commands = {'install': ['setup', 'install'], 'resume': ['setup', 'install', '--resume'], 'accounts': ['setup', 'run'], 'docker': ['containers', 'provision']}
        if operation == 'retry':
            if item not in {row['key'] for row in setup_plan.items()[1]}:
                raise ValueError('Item is not selected in the saved plan')
            commands['retry'] = ['setup', 'install', '--item', item]
        if operation not in commands:
            raise ValueError('Unknown setup operation.')
        self.process = subprocess.Popen([terminal, '--separate', '--nofork', '-e',
                                         str(core.ROOT/'bin/deckctl'), *commands[operation]])
        self.operation = "install" if operation in ("resume", "retry") else operation
        return self.progress()

    def log(self, item):
        if item not in {row['key'] for row in setup_plan.items()[1]}:
            raise ValueError('Unknown installation item')
        text = install_log.read(item)
        return {'item': item, 'text': text[-65536:], 'truncated': len(text) > 65536,
                'updatedAt': install_log.path_for(item).stat().st_mtime}

    def progress(self):
        state = setup_install.snapshot()
        plan, rows = setup_plan.items()
        matches = state.get('fingerprint') == setup_plan.fingerprint(plan)
        records = state.get('items', {}) if matches else {}
        live = state.get('running', False) or bool(self.process and self.process.poll() is None)
        visible = [{**row, **records.get(row['key'], {'status': 'PENDING', 'message': ''}), 'id': row['key']}
                   for row in rows if row['visible']]
        now = time.time()
        for row in visible:
            status = row.get('status')
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
            activity = max(row.get('updatedAt') or start or now, path.stat().st_mtime if row['hasLog'] else 0)
            row['quietSeconds'] = max(0, int(now-activity))
            row['activityNotice'] = ('No new output for '+str(row['quietSeconds'])+
                                     's. This may be a quiet operation or a prompt in Konsole; check Details before retrying.') if row.get('status') == 'RUNNING' and row['quietSeconds'] >= 90 else ''
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
        return {'running': live, 'operation': operation, 'summary': summary,
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
            try:
                if post:
                    size = int(self.headers.get('Content-Length', '0'))
                    if size < 1 or size > 16384:
                        raise ValueError('Invalid request size')
                    payload = json.loads(self.rfile.read(size))
                    if not isinstance(payload, dict):
                        raise ValueError('Expected an object')
                    if route == 'inventory':
                        result = session.inventory(refresh=True)
                    elif route == 'save':
                        result = session.save(payload)
                    elif route == 'start':
                        result = session.start(payload.get('operation'), payload.get('item'))
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
                else:
                    raise ValueError('Unknown view')
                self.reply(200, result)
            except (BrokenPipeError, ConnectionResetError):
                pass  # Closing the UI may abandon a pending read-only request.
            except (ValueError, OSError, RuntimeError, SystemExit) as exc:
                self.reply(400, {'error': str(exc)})

        def do_GET(self):
            self.handle_request()

        def do_POST(self):
            self.handle_request(True)

    with HTTPServer(('127.0.0.1', 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            env = dict(os.environ, QT_QUICK_CONTROLS_STYLE='Basic')
            result = subprocess.call([runtime, str(core.ROOT/'lib/deckctl/ui/Setup.qml'), '--',
                                      f'http://127.0.0.1:{server.server_port}/{token}/'], env=env)
            return result or (2 if plan_only and session.selected is None else 0)
        finally:
            if session.inventory_scan: session.inventory_scan.close()
            server.shutdown()
            thread.join()
