"""On-demand Qt Quick setup window using SteamOS's existing QML runtime."""
from __future__ import annotations
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from . import apps, core, setup_builder, gaming_options


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

    def snapshot(self):
        manifests = core.module_manifests()
        return {'groups': setup_builder.catalog()['groups'],
                'apps': [{'id': key, 'name': app['name'], 'summary': APP_DESCRIPTIONS.get(key, 'Optional desktop app'),
                          'module': app['module']} for key, app in apps.catalog().items()],
                'modules': core.enabled_modules(), 'selectedApps': apps.selection(),
                'defaults': list(manifests),
                'launchers': gaming_options.ITEMS, 'selectedLaunchers': gaming_options.selection(),
                'plugins': setup_builder.plugin_items(), 'selectedPlugins': sorted(core._decky_selected_folders()),
                'defaultPlugins': core._decky_default_selection(),
                'dependencies': {key: item[1].get('depends_on', []) for key, item in manifests.items()},
                'planOnly': self.plan_only}

    def save(self, payload):
        if self.process and self.process.poll() is None:
            raise ValueError('Wait for the current operation to finish before changing your plan.')
        roots = payload.get('modules')
        selected = payload.get('apps')
        known = core.module_manifests()
        if (not isinstance(roots, list) or not isinstance(selected, list)
                or any(not isinstance(x, str) or x not in known for x in roots)
                or any(not isinstance(x, str) or x not in apps.catalog() for x in selected)):
            raise ValueError('Invalid feature or app selection. Reopen setup and try again.')
        normalized = setup_builder._app_module_roots(roots, selected)
        setup_builder.save_plan(normalized, selected, payload.get("launchers"), payload.get("plugins"))
        self.selected = core.topo(normalized)
        return {'saved': True, 'modules': self.selected}

    def start(self, operation):
        if self.plan_only:
            raise ValueError('Continue installation in the installer after saving this plan.')
        if not self.selected:
            raise ValueError('Review and save a plan first.')
        if self.process and self.process.poll() is None:
            raise ValueError('An operation is already running.')
        terminal = shutil.which('konsole')
        if not terminal:
            raise ValueError('Konsole is required for interactive installer prompts.')
        commands = {'install': ['apply'], 'accounts': ['setup', 'run'], 'docker': ['containers', 'provision']}
        if operation not in commands:
            raise ValueError('Unknown setup operation.')
        self.process = subprocess.Popen([terminal, '--separate', '--nofork', '-e',
                                         str(core.ROOT/'bin/deckctl'), *commands[operation]])
        self.operation = operation
        return self.progress()

    def progress(self):
        records = core.load_json(core.STATE/'provisioning.json', {}).get('modules', {})
        version = (core.ROOT/'VERSION').read_text().strip()
        records = {mid: row for mid, row in records.items() if row.get('version') == version}
        return {'running': bool(self.process and self.process.poll() is None),
                'operation': self.operation,
                'exitCode': self.process.poll() if self.process else None,
                'modules': [{'id': mid, 'status': records.get(mid, {}).get('status', 'PENDING'),
                             'message': records.get(mid, {}).get('message', '')}
                            for mid in (self.selected or [])]}


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
                    if route == 'save':
                        result = session.save(payload)
                    elif route == 'start':
                        result = session.start(payload.get('operation'))
                    else:
                        raise ValueError('Unknown operation')
                elif route == 'catalog':
                    result = session.snapshot()
                elif route == 'progress':
                    result = session.progress()
                else:
                    raise ValueError('Unknown view')
                self.reply(200, result)
            except (ValueError, OSError, RuntimeError) as exc:
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
            server.shutdown()
            thread.join()
