"""Read-only per-item installation plans shared by the window and install runner."""
from __future__ import annotations
import hashlib
import json
import os
import re
import math
from pathlib import Path
import shutil
import subprocess
import urllib.error
from datetime import datetime, timezone
from . import core, apps, component_options, gaming_options, css_stack, setup_builder, appearance, css_connection

GROUPS = {'terminal', 'dev', 'remote', 'media', 'workspace', 'gaming', 'utilities'}
FLATPAKS = {'remote:moonlight': 'com.moonlight_stream.Moonlight',
            'remote:chiaki': 'io.github.streetpea.Chiaki4deck',
            'launcher:heroic': 'com.heroicgameslauncher.hgl',
            'launcher:protonplus': 'com.vysp3r.ProtonPlus', 'dependency:chrome': 'com.google.Chrome'}
SIGN_IN = {'discord', 'slack', 'whatsapp', 'telegram', 'spotify', 'plex', 'parsec'}
GIB = 1024 ** 3


def saved():
    enabled = set(core.enabled_modules())
    return {'modules': core.enabled_modules(), 'apps': [key for key in apps.selection() if apps.catalog()[key]['module'] in enabled],
            'components': {group: values if group in enabled else [] for group, values in component_options.selection().items()},
            'launchers': gaming_options.selection() if 'gaming' in enabled else [],
            'plugins': sorted(core._decky_selected_folders()) if 'decky' in enabled else [],
            'css': css_stack.selection() if 'decky' in enabled else [],
            'palette': css_stack.palette_id(), 'appearance': appearance.selection()}


def normalize(payload):
    if not isinstance(payload, dict): raise ValueError('Expected an installation plan')
    roots = payload.get('modules')
    names = payload.get('apps')
    if (not isinstance(roots, list) or any(not isinstance(n, str) or n not in core.module_manifests() for n in roots)
            or len(roots) != len(set(roots))): raise ValueError('Invalid modules in plan')
    if not isinstance(names, list) or any(not isinstance(n, str) for n in names): raise ValueError('Invalid apps in plan')
    names = apps.known(names)
    components = component_options.validate(payload.get('components', {}))
    components = {key: sorted(components.get(key, [])) for key in component_options.CATALOG}
    launchers = gaming_options.validate(payload.get('launchers', []))
    css = css_stack.validate_selection(payload.get('css', []))
    plugins = payload.get('plugins', [])
    known = {item['id'] for item in setup_builder.plugin_items()}
    if not isinstance(plugins, list) or any(not isinstance(n, str) or n not in known for n in plugins):
        raise ValueError('Invalid plugins in plan')
    plugins = sorted(set(plugins) | ({'SDH-CssLoader'} if css else set()))
    roots = set(roots) | {'base'}
    roots.update(group for group, values in components.items() if values)
    if launchers: roots.add('gaming')
    if plugins: roots.add('decky')
    roots = set(setup_builder._app_module_roots(roots, names))
    if 'ai-workspace' in roots:
        components['terminal'] = sorted(set(components['terminal']) | {'opencode'})
        roots.add('terminal')
    if {'model', 'model-7b'}.intersection(components['ai-workspace']):
        components['ai-workspace'] = sorted(set(components['ai-workspace']) | {'ollama'})
    return {'modules': sorted(roots), 'apps': sorted(names), 'components': components,
            'launchers': launchers, 'plugins': plugins, 'css': css,
            'palette': css_stack.validate_palette(payload.get('palette', 'bubblegum')),
            'appearance': appearance.validate(payload.get('appearance', {}))}


def fingerprint(plan):
    return hashlib.sha256(json.dumps({'plan': plan, 'version': (core.ROOT/'VERSION').read_text().strip()}, sort_keys=True).encode()).hexdigest()


def items(payload=None):
    plan = normalize(saved() if payload is None else payload)
    manifests = core.module_manifests()
    rows = {}
    def add(key, name, kind, owner, detail='', requires=(), **extra):
        rows[key] = dict(key=key, name=name, kind=kind, owner=owner, detail=detail,
                         requires=list(requires), **extra)
    # Category-only nodes carry dependencies without installing optional bundles.
    for mid in core.topo(plan['modules']):
        add('module:'+mid, manifests[mid][1]['name'], 'support' if mid in GROUPS else 'module', mid,
            requires=['module:'+dep for dep in manifests[mid][1].get('depends_on', [])])
    for key in plan['apps']:
        app = apps.catalog()[key]
        add('app:'+key, app['name'], 'flatpak', app['module'], requires=['module:'+app['module']],
            flatpak=app['id'], followup='signin' if key in SIGN_IN else '', app_key=key)
    for group, options in component_options.catalog().items():
        if group not in plan['modules']: continue
        for option in options:
            name = option['id']
            if name not in plan['components'][group]: continue
            key = group+':'+name
            deps = ['module:'+group]
            if group == 'ai-workspace' and name.startswith('model'): deps.append('ai-workspace:ollama')
            if group in ('workspace', 'media'): deps.append('dependency:chrome')
            followup = ('pairing' if key in ('remote:moonlight', 'remote:chiaki') else
                        'signin' if (group in ('workspace', 'media') and key != 'media:tinyfingers') or key in ('dev:codex', 'dev:claude-code', 'remote:tailscale', 'media:keeper') else '')
            add(key, option['name'], 'component', group, option['summary'], deps,
                component=name, followup=followup)
    for option in gaming_options.ITEMS:
        if option['id'] in plan['launchers']:
            add('launcher:'+option['id'], option['name'], 'launcher', 'gaming', option['summary'],
                ['module:gaming'], component=option['id'], followup='signin' if option['id'] in ('heroic', 'battlenet') else 'setup' if option['id'] == 'nonsteamlaunchers' else '')
    for option in setup_builder.plugin_items():
        if option['id'] in plan['plugins']:
            add('plugin:'+option['id'], option['name'], 'plugin', 'decky', option['summary'], ['module:decky'], component=option['id'])
    needs_css = bool(plan['css'] or (plan['appearance'].get('css', True) and css_stack.installed_palette_components()))
    if needs_css:
        add(css_connection.KEY, 'CSS Loader connection', 'css-connection', 'decky',
            'Shared by the selected CSS themes and palette. Retry here, then Resume the queue.',
            ['plugin:SDH-CssLoader'] if 'plugin:SDH-CssLoader' in rows else [])
    for option in css_stack.selection_items():
        if option['id'] in plan['css']:
            add('css:'+option['id'], option['name'], 'css', 'decky', option['summary'], [css_connection.KEY], component=option['id'])
    if needs_css:
        add('dependency:css-profile', 'CSS palette and recovery profile', 'css-profile', 'decky',
            requires=[css_connection.KEY] + ['css:'+name for name in plan['css']])
    if any('dependency:chrome' in row['requires'] for row in rows.values()):
        add('dependency:chrome', 'Google Chrome', 'flatpak', 'base', 'Shared by your selected web shortcuts and browser extensions.', ['module:base'], flatpak=FLATPAKS['dependency:chrome'])
    if 'module:ai-workspace' in rows:
        rows['module:ai-workspace']['requires'].append('terminal:opencode')
    for key, row in rows.items():
        if key in FLATPAKS: row['flatpak'] = FLATPAKS[key]
        row['visible'] = row['kind'] != 'support'
    ordered, seen, visiting = [], set(), set()
    def visit(key):
        if key in seen: return
        if key in visiting or key not in rows: raise ValueError('Invalid install dependency: '+key)
        visiting.add(key)
        for dep in rows[key]['requires']: visit(dep)
        visiting.remove(key); seen.add(key); ordered.append(rows[key])
    for key in rows: visit(key)
    return plan, ordered


def command(args, timeout=8):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=dict(os.environ, LC_ALL='C'))
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired): return None


def binary(name):
    local = Path.home()/'.local/bin'/name
    return str(local) if local.is_file() and os.access(local, os.X_OK) else shutil.which(name)


def present(row):
    """Return installed evidence, separately from account/pairing readiness."""
    key = row['key']
    if row['kind'] == 'css-connection': return css_connection.status()
    if 'flatpak' in row:
        commit = command(['flatpak', 'info', '--show-commit', row['flatpak']])
        scope = 'user' if command(['flatpak', 'info', '--user', '--show-commit', row['flatpak']]) else 'system'
        details = {'commit': commit, 'scope': scope,
                              'origin': command(['flatpak', 'info', '--'+scope, '--show-origin', row['flatpak']]) if commit else 'flathub',
                              'ref': command(['flatpak', 'info', '--'+scope, '--show-ref', row['flatpak']]) if commit else row['flatpak']}
        if key.startswith('app:') and key.removeprefix('app:') in apps.GAMING_KEYS:
            state = apps.gaming_status(key.removeprefix('app:'))
            details.update(shortcutState=state, configured=state == 'READY', configuration=bool(commit) and state != 'READY')
        return bool(commit), details
    if row['kind'] == 'support': return True, {}
    if row['kind'] == 'plugin':
        installed = core._decky_installed_plugins().get(row['component'], {})
        return bool(installed.get('valid')), installed
    if row['kind'] == 'css':
        theme = css_stack._find(css_stack._installed_themes(), row['component'])
        ready = css_stack.component_ready(row['component'])
        return bool(theme), {'version':theme['manifest'].get('version') if theme else None,
                             'configured':ready, 'configuration':bool(theme) and not ready,
                             'message':('Theme files detected. Saved palette/enabled settings still need verification.' if theme and not ready else '')}
    if row['kind'] == 'css-profile': return css_stack.readiness()[0], {}
    if key.startswith('terminal:'):
        from . import terminal
        name = row['component']
        if name == 'fonts': return terminal._fonts_ok(core.load_json(terminal.RECEIPTS_FILE, {})), {}
        if name == 'konsole' and not appearance.enabled('konsole'): return True, {'configuration': False}
        if name in ('shell', 'konsole'):
            state = terminal.status_data()
            keys = ('shell_config',) if name == 'shell' else ('konsole_profile', 'konsole_scheme', 'konsole_default')
            return all(state.get(key) for key in keys), {'configuration': True}
        path = binary(name)
        version = command([path, '-V' if name == 'tmux' else '--version']) if path else None
        return bool(version), {'version': version}
    if key == 'remote:tailscale':
        from . import tailscale
        state = tailscale.status()
        return state['installed'], {**state, 'configured':state['connected']}
    if key in ('dev:codex', 'dev:claude-code', 'ai-workspace:ollama'):
        name = {'dev:claude-code': 'claude', 'remote:tailscale': 'tailscale', 'ai-workspace:ollama': 'ollama'}.get(key, 'codex')
        path = binary(name)
        version = command([path, '--version']) if path else None
        return bool(version), {'version': version}
    if key.startswith('ai-workspace:model'):
        from . import ai_workspace
        model = next(model for model, data in ai_workspace.LOCAL_MODELS.items() if data['component'] == row['component'])
        return ai_workspace.model_present(model), {'model': model}
    if key == 'dev:docker':
        from . import containers
        state = containers.status_data()
        return state.get('status') == 'READY', state
    if key == 'dev:distrobox':
        listing = command(['distrobox', 'list', '--no-color']) or ''
        return any('deck-dev' in line.split('|') or 'deck-dev' in line.split() for line in listing.splitlines()), {}
    if row['owner'] == 'workspace':
        path = Path.home()/'.local/share/applications'/('deck-workspace-'+row['component']+'.desktop')
        details = {}
        if key == 'workspace:chatgpt':
            from . import app_shortcuts
            state = app_shortcuts.status(key, 'ChatGPT', path)
            details.update(shortcutState=state, configured=state == 'READY', configuration=path.is_file() and state != 'READY')
        return path.is_file(), details
    if key == 'media:keeper': return core._keeper_installed(), {}
    if row['owner'] == 'media' and row['kind'] == 'component':
        path = Path.home()/'.local/share/applications'/('deck-media-'+row['component']+'.desktop')
        details = {}
        if key == 'media:tinyfingers':
            from . import app_shortcuts
            state = app_shortcuts.status(key, 'TinyFingers', path)
            details.update(shortcutState=state, configured=state == 'READY', configuration=path.is_file() and state != 'READY')
        return path.is_file(), details
    if key == 'module:decky': return core._decky_loader_present(), {}
    if key == 'launcher:battlenet':
        from . import launchers
        return launchers.battlenet_installed(), {}
    if key == 'launcher:nonsteamlaunchers': return (Path.home()/'Desktop/Deck-Setup-Staged/NonSteamLaunchers.desktop').is_file(), {}
    if key == 'module:ai-workspace':
        from . import ai_workspace
        try:
            value = json.loads(ai_workspace.CONFIG.read_text())
            valid = ai_workspace.merge_config(value, ai_workspace.config_data()) == value
        except (OSError, ValueError, TypeError): valid = False
        return valid, {'configuration': True}
    if row['kind'] == 'module':
        state = core.module_status(row['owner'])
        return state.get('status') in ('READY', 'OPTIONAL'), state
    return False, {}


def storage_budget(row, installed):
    """Free-space allowances, not fabricated exact download totals."""
    from . import ai_workspace
    path = Path.home()
    if row['kind'] == 'css-connection': return path, 0, 'Shared local connection; no download'
    if row['key'].startswith('ai-workspace:model'):
        data = next(data for data in ai_workspace.LOCAL_MODELS.values() if data['component'] == row['component'])
        return ai_workspace.MODELS, data['space_bytes'], 'Model staging allowance'
    if row['key'] == 'ai-workspace:ollama': return ai_workspace.DATA, 8*GIB, 'Runtime staging allowance'
    if row['key'] in ('dev:claude-code', 'dev:codex'): return Path.home()/'.local', GIB, 'CLI installation allowance'
    if row['key'].startswith('terminal:') and row.get('component') not in ('shell', 'konsole'):
        return Path.home()/'.local', GIB//2, 'Tool staging allowance'
    if row['kind'] in ('css', 'plugin'): return Path.home()/'homebrew', 128*1024**2, 'Theme/plugin staging allowance'
    return path, None, 'Size checked by the provider installer'


def _size(details, label):
    match = re.search(r'^\s*'+re.escape(label)+r':\s*([0-9]+(?:\.[0-9]+)?)\s*(bytes?|[kKMGT]i?B)\s*$', details, re.MULTILINE)
    if not match: return None
    units = {'byte': 1, 'bytes': 1, 'kB': 1000, 'KB': 1000, 'MB': 1000**2, 'GB': 1000**3, 'TB': 1000**4,
             'KiB': 1024, 'MiB': 1024**2, 'GiB': 1024**3, 'TiB': 1024**4}
    # Round upward by a displayed unit to avoid treating rounded metadata as exact.
    unit = units[match[2]]
    return math.ceil((float(match[1]) + (0.1 if '.' in match[1] else 1))*unit)


def review_notes(row):
    key = row['key']
    notes = []
    if key == 'remote:tailscale':
        notes.append('Setup stays in this window. A KDE password dialog authorizes the service; sign-in opens in your browser. Retry here after signing in.')
    elif key == 'launcher:battlenet':
        notes.append('Setup starts here with live console output. Complete any Battle.net installer or login windows; no terminal is required.')
    elif key == 'module:android':
        notes.append('Setup runs in this queue and console. Follow the Android image chooser or Google Play window, then close Android for verification. App administrator authorization is reused; Retry preserves images and apps.')
    elif row['kind'] in css_connection.KINDS:
        notes.append('Prefers live CSS without sudo. Normal Desktop fallback uses the KDE administrator dialog. Retry the connection here, then Resume.')
    elif row['kind'] == 'plugin':
        notes.append('A KDE password dialog requests sudo when needed and reuses temporary authorization until this app closes. The password is never saved; Cancel leaves this item retryable.')
    elif key == 'module:decky':
        notes.append('Vendor setup may need its interactive window or Konsole, including sudo authorization.')
    elif 'flatpak' in row:
        notes.append('Uses the existing system app or installs in your user account.')
    else:
        notes.append('Privileges depend on the provider; any administrator prompt stays in Konsole.')
    if row['kind'] in css_connection.KINDS:
        notes.append('Normal Desktop fallback may restart Decky temporarily. Nested Desktop never restarts Decky or Steam; no session switch is requested.')
    elif key == 'module:decky':
        notes.append('May restart Decky; check the result in Game Mode.')
    elif key == 'module:controller':
        notes.append('Switch to Game Mode to reload templates; restart Steam only if still missing.')
    elif key.startswith('terminal:'):
        notes.append('Open a new terminal for configuration changes; an existing tmux session may need restarting after an upgrade.')
    elif key == 'module:android':
        notes.append('Follow vendor instructions for service or device restarts.')
    else:
        notes.append('No automatic device reboot; follow any provider restart instructions.')
    if row.get('followup'): notes.append('After installation: '+{'signin':'sign in to your account','pairing':'pair your device','setup':'complete vendor setup'}.get(row['followup'],'check setup')+'.')
    return notes


def update_failure(result, exc):
    """Explain failed metadata checks without exposing URLs or response bodies."""
    result['updateCheck'] = 'Unavailable; installer will check'
    result['updateReason'] = 'The provider could not return usable update metadata.'
    result['updateNextAction'] = 'Check connectivity and use Refresh status to retry. Other components can still be installed.'
    if isinstance(exc, urllib.error.HTTPError):
        headers = exc.headers or {}
        limited = exc.code == 429 or (exc.code == 403 and headers.get('X-RateLimit-Remaining') == '0')
        result['updateReason'] = 'The provider’s API request limit was reached.' if limited else f'The provider rejected the metadata request (HTTP {exc.code}).'
        reset = headers.get('X-RateLimit-Reset', '')
        if limited and reset.isdigit() and 0 < int(reset) < 253402300800:
            when = datetime.fromtimestamp(int(reset), timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
            result['updateNextAction'] = f'The provider reports a limit reset at {when}. Refresh status after that time; other components remain available.'
    elif isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)):
        result['updateReason'] = 'The update provider timed out.'
    elif isinstance(exc, urllib.error.URLError):
        result['updateReason'] = 'The update provider could not be reached (network, DNS or TLS failure).'
    elif isinstance(exc, ValueError):
        result['updateReason'] = 'The provider returned metadata that could not be read safely.'


def inspect(row, online=False):
    installed, evidence = present(row)
    result = {**row, 'installed': installed, 'action': 'INSTALLED' if installed else 'NEW',
              'updateCheck': 'Not checked', 'downloadBytes': None, 'installedVersion': evidence.get('version'),
              'reviewNotes': review_notes(row)}
    if row['kind'] == 'support': result['action'] = 'SUPPORT'
    if evidence.get('configuration') or row['kind'] == 'css-profile': result['action'] = 'CONFIGURE'
    if installed and 'flatpak' in row and evidence.get('scope') == 'system':
        result.update(action='PRESERVE_SYSTEM', updateCheck='System installation is reused; update through its owner')
    elif online and 'flatpak' in row:
        scope = '--'+evidence.get('scope', 'user') if installed else '--user'
        remote = command(['flatpak', 'remote-info', scope, '--show-commit', evidence.get('origin') or 'flathub', evidence.get('ref') or row['flatpak']], timeout=20)
        if remote:
            result['updateCheck'] = 'Checked'
            result['installedVersion'] = evidence.get('commit')
            result['availableVersion'] = remote
            if installed: result['action'] = 'UP_TO_DATE' if remote == evidence.get('commit') else 'UPDATE'
        else: result['updateCheck'] = 'Unavailable; installer will check'
        details = command(['flatpak', 'remote-info', scope, evidence.get('origin') or 'flathub', evidence.get('ref') or row['flatpak']], timeout=20)
        if details:
            result['downloadBytes'] = _size(details, 'Download size')
            result['providerInstalledBytes'] = _size(details, 'Installed size')
    elif online and row['key'].startswith('ai-workspace:model'):
        from . import ai_workspace, terminal
        try:
            name, tag = evidence['model'].split(':')
            remote = json.loads(terminal._request(f'https://registry.ollama.ai/v2/library/{name}/manifests/{tag}', 20))
            if not isinstance(remote, dict) or not isinstance(remote.get('layers'), list) or not isinstance(remote.get('config'), dict):
                raise ValueError('Invalid model metadata')
            layers = [remote['config'], *remote['layers']]
            if any(not isinstance(layer, dict) or type(layer.get('size')) is not int or layer['size'] < 0 for layer in layers):
                raise ValueError('Invalid model size')
            result['downloadBytes'] = sum(layer['size'] for layer in layers)
            local = core.load_json(ai_workspace.MODELS/'manifests/registry.ollama.ai/library'/evidence['model'].replace(':', '/'), {})
            needed = remote != local
            result['updateCheck'] = 'Checked'
            if installed: result['action'] = 'UPDATE' if needed else 'UP_TO_DATE'
        except (OSError, ValueError, RuntimeError) as exc: update_failure(result, exc)
    elif online and row['key'].startswith('terminal:'):
        from . import terminal
        name = row.get('component')
        if name in terminal.UPDATE_REPOS:
            receipts = core.load_json(terminal.RECEIPTS_FILE, {})
            receipt = receipts.get(name, {})
            if installed and (not receipt or (name != 'fonts' and not terminal._receipt_binary_ok(name, receipts))):
                result['updateCheck'] = 'Existing unmanaged tool; preserved'
            else:
                try:
                    release = terminal._github_latest(terminal.UPDATE_REPOS[name])
                    result['availableVersion'] = release.get('tag_name')
                    newer = terminal.newer_version(release.get('tag_name'), receipt.get('version'))
                    result['updateCheck'] = 'Checked' if newer is not None or not installed else 'Version comparison unavailable'
                    if installed and newer is not None: result['action'] = 'UPDATE' if newer else 'UP_TO_DATE'
                except (OSError, ValueError, RuntimeError) as exc: update_failure(result, exc)
    path, budget, label = storage_budget(row, installed)
    if result.get('providerInstalledBytes') is not None and result['downloadBytes'] is not None:
        budget = result['providerInstalledBytes'] + result['downloadBytes']
        path = Path.home()/'.local/share/flatpak'
        label = 'Provider estimate plus download staging; shared Flatpak runtimes are additional'
    result.update(storagePath=str(path), spaceBytes=budget, spaceLabel=label)
    return result


def preview(payload=None, online=False):
    from concurrent.futures import ThreadPoolExecutor
    plan, rows = items(payload)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda row: inspect(row, online), rows))
    volumes = {}
    unknown = 0
    for row in results:
        if not row['visible'] or row['action'] in ('UP_TO_DATE', 'CONFIGURE', 'PRESERVE_SYSTEM'): continue
        if row['spaceBytes'] is None:
            unknown += 1
            continue
        anchor = Path(row['storagePath']).resolve()
        while not anchor.exists(): anchor = anchor.parent
        device = anchor.stat().st_dev
        volume = volumes.setdefault(device, {'path': str(anchor), 'requiredBytes': GIB, 'reserveBytes': GIB, 'freeBytes': shutil.disk_usage(anchor).free})
        volume['requiredBytes'] += row['spaceBytes']
    for volume in volumes.values(): volume['fits'] = volume['freeBytes'] >= volume['requiredBytes']
    return {'plan': plan, 'fingerprint': fingerprint(plan), 'items': results, 'volumes': list(volumes.values()),
            'unknownSizes': unknown, 'canInstall': all(volume['fits'] for volume in volumes.values()),
            'sizeNote': 'Allowances include staging space and 1 GiB headroom per filesystem. Unknown sizes and shared Flatpak runtimes are checked by their installers.'}
