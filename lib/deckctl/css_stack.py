"""Converge real Theme Store components through CSS Loader's native backend.

No CSS payloads, private API tokens, alternate theme downloader, or config-file
writes live here. The installed plugin owns downloads, dependencies and settings.
See modules/decky/README.md for the supported backend contract and failure states.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
import hashlib
import json
import re
import shutil
import time
import urllib.parse
import urllib.request
from pathlib import Path

from . import core, decky_installer

STACK_PATH = core.ROOT / 'modules/decky/css-stack.json'
THEMES_DIR = Path.home() / 'homebrew/themes'
PLUGIN_DIR = Path.home() / 'homebrew/plugins/SDH-CssLoader'
RECEIPT = core.CONFIG_HOME / 'css-stack-receipt.json'
STORE_API = 'https://api.deckthemes.com'
BACKEND_URL = 'http://127.0.0.1:35821/req'
MAX_RESPONSE = 8 * 1024 * 1024


class CSSError(RuntimeError):
    pass


def palette_catalog():
    return core.load_json(core.ROOT/'config/setup-palettes.json', [])


def validate_palette(key):
    if not isinstance(key, str) or key not in {item['id'] for item in palette_catalog()}:
        raise ValueError('Unknown theme palette')
    return key


def palette_id():
    return validate_palette(core.load_json(core.CONFIG_HOME/'css-selection.json', {}).get('palette', 'bubblegum'))


def _stack(unfiltered=False):
    data = json.loads(STACK_PATH.read_text())
    if data.get('schema_version') != 3 or not data.get('required'):
        raise CSSError('Invalid CSS stack manifest')
    palette = next(item for item in palette_catalog() if item['id'] == palette_id())
    data['palette'] = palette['css_palette']
    data['palette_name'] = palette['name']
    data['named_presets'] = palette['named_presets']
    data['preset'] = palette['name'] + ' - Base'
    from . import appearance
    data['apply_palette'] = appearance.enabled('css')
    if not data['apply_palette']:
        data['palette_name'] = 'Existing colors'
        data['preset'] = 'Deckctl - Existing colors'
        for item in data['required'] + data['recommended'] + data.get('optional', []):
            item['configure_palette'] = False
    if not unfiltered:
        names = selection()
        items = data['required'] + data['recommended'] + data.get('optional', [])
        data['required'] = [item for item in items if item['name'] in names]
        data['recommended'] = []
    return data


def selection():
    data = _stack(unfiltered=True)
    state = core.load_json(core.CONFIG_HOME/'css-selection.json', None)
    defaults = [item['name'] for item in data['required'] + data['recommended']]
    return validate_selection(state['selected']) if state is not None else defaults


def validate_selection(values):
    data = _stack(unfiltered=True)
    known = {item['name'] for category in ('required', 'recommended', 'optional') for item in data.get(category, [])}
    if not isinstance(values, (list, set, tuple)) or any(not isinstance(x,str) or x not in known for x in values):
        raise ValueError('Invalid CSS Loader component selection')
    return sorted(set(values))


def selection_items():
    data = _stack(unfiltered=True)
    return [{'id': item['name'], 'name': item['name'], 'summary': item.get('reason', '')}
            for category in ('required', 'recommended', 'optional') for item in data.get(category, [])]


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _key(name):
    return ''.join(c for c in str(name).casefold() if c.isalnum())


def _installed_themes():
    out = {}
    if not THEMES_DIR.is_dir():
        return out
    for child in sorted(THEMES_DIR.iterdir()):
        manifest = child / 'theme.json'
        if not child.is_dir() or child.is_symlink() or not manifest.is_file():
            continue
        try:
            data = _read(manifest)
            name = data.get('display_name') or data['name']
            out[name.casefold()] = {'name': name, 'path': child, 'manifest': data}
        except (OSError, ValueError, KeyError):
            continue
    return out


def _find(installed, wanted):
    matches = [v for k, v in installed.items() if _key(k) == _key(wanted)]
    if len(matches) > 1:
        raise CSSError(f'Ambiguous installed component: {wanted}')
    return matches[0] if matches else None


def _fetch_json(url, payload=None, timeout=30):
    headers = {'User-Agent': 'deckctl/' + (core.ROOT / 'VERSION').read_text().strip()}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers)
    # Loopback calls must never be forwarded through a user's HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({})) if url == BACKEND_URL else urllib.request.build_opener()
    with opener.open(req, timeout=timeout) as response:
        raw = response.read(MAX_RESPONSE + 1)
    if len(raw) > MAX_RESPONSE:
        raise CSSError('CSS response exceeds size limit')
    return json.loads(raw)


class Backend:
    def call(self, method, **args):
        envelope = _fetch_json(BACKEND_URL, {'method': method, 'args': args}, timeout=180 if method == 'download_theme_from_url' else 20)
        if not isinstance(envelope, dict) or envelope.get('success') is not True or 'res' not in envelope:
            raise CSSError(f'CSS Loader {method} failed: {envelope}')
        result = envelope['res']
        if isinstance(result, dict):
            if result.get('success') is False or result.get('fails'):
                raise CSSError(f'CSS Loader {method} failed: {result}')
        return result

    def themes(self):
        data = self.call('get_themes')
        if not isinstance(data, list) or any(not isinstance(t, dict) or not isinstance(t.get('name'), str) or not isinstance(t.get('patches'), list) for t in data):
            raise CSSError('Unsupported CSS Loader theme schema')
        return data


def _validate_plugin():
    """Check the installed interface before enabling its optional loopback bridge."""
    if _read(PLUGIN_DIR / 'plugin.json').get('name') != 'CSS Loader':
        raise CSSError('Installed plugin identity is not CSS Loader')
    tree = ast.parse((PLUGIN_DIR / 'main.py').read_text())
    methods = {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    required = {'get_themes', 'fetch_theme_path', 'get_backend_version', 'download_theme_from_url', 'set_theme_state', 'set_patch_of_theme', 'set_component_of_theme_patch', 'reset', 'generate_preset_theme_from_theme_names'}
    if not required <= methods:
        raise CSSError('Installed CSS Loader lacks required native methods: ' + ', '.join(sorted(required - methods)))
    # Only the upstream loopback bridge and upstream sentinel convention are supported.
    server = ast.parse((PLUGIN_DIR / 'css_server.py').read_text())
    constants = {n.value for n in ast.walk(server) if isinstance(n, ast.Constant) and isinstance(n.value, (str, int))}
    if not {'127.0.0.1', 35821, '/req'} <= constants:
        raise CSSError('CSS Loader loopback bridge changed; no configuration was guessed')
    utils = (PLUGIN_DIR / 'css_utils.py').read_text()
    if 'def store_or_file_config' not in utils or 'key.upper()' not in utils:
        raise CSSError('CSS Loader server enablement contract changed')


@contextmanager
def _backend_session():
    _validate_plugin()
    backend = Backend()
    sentinel = THEMES_DIR / 'SERVER'
    created = False
    try:
        try:
            backend.themes()
        except (OSError, ValueError, CSSError):
            THEMES_DIR.mkdir(parents=True, exist_ok=True)
            if not sentinel.exists():
                sentinel.touch(exist_ok=False)
                created = True
            print('Starting CSS Loader native configuration bridge (Decky restart).')
            if not decky_installer._restart_decky():
                raise CSSError('Could not restart Decky for CSS Loader configuration')
            deadline = time.monotonic() + 30
            while True:
                try:
                    backend.themes()
                    break
                except (OSError, ValueError, CSSError):
                    if time.monotonic() >= deadline:
                        raise CSSError('CSS Loader backend did not become ready within 30 seconds')
                    time.sleep(1)
        if Path(backend.call('fetch_theme_path')).resolve() != THEMES_DIR.resolve():
            raise CSSError('CSS Loader uses a different theme directory; refusing to modify the wrong tree')
        version = backend.call('get_backend_version')
        if not isinstance(version, int) or version < 9:
            raise CSSError('CSS Loader manifest support 9 or newer is required for configurable colors')
        yield backend
    finally:
        if created:
            sentinel.unlink(missing_ok=True)
            if not decky_installer._restart_decky():
                raise CSSError('Settings saved, but Decky restart failed while closing the temporary CSS bridge; retry setup')


def _resolve_store_theme(name):
    """Same search/detail endpoints used by CSS Loader's Theme Store UI."""
    matches = {}
    for page in range(1, 21):
        query = urllib.parse.urlencode({'search': name, 'page': page, 'perPage': 50, 'filters': 'BPM-CSS.-Preset'})
        data = _fetch_json(f'{STORE_API}/themes?{query}')
        if not isinstance(data, dict) or not isinstance(data.get('items'), list) or not isinstance(data.get('total'), int):
            raise CSSError('Theme Store search schema changed')
        for item in data['items']:
            if _key(name) in {_key(item.get('name', '')), _key(item.get('displayName', ''))} and item.get('type', 'Css') == 'Css':
                matches[item['id']] = item
        if page * 50 >= data['total']:
            break
    else:
        raise CSSError(f'Theme Store search exceeded pagination limit for {name}')
    if len(matches) != 1:
        raise CSSError(f'Theme Store must return one exact match for {name}; found {len(matches)}')
    item = next(iter(matches.values()))
    ident = str(item['id'])
    detail = _fetch_json(f'{STORE_API}/themes/{urllib.parse.quote(ident, safe="")}')
    if detail.get('disabled') or detail.get('approved') is False or detail.get('type', 'Css') != 'Css':
        raise CSSError(f'Theme Store component unavailable: {name}')
    if _key(name) not in {_key(detail.get('name', '')), _key(detail.get('displayName', ''))} or str(detail.get('id')) != ident:
        raise CSSError(f'Theme Store identity mismatch: {name}')
    if not isinstance(detail.get('manifestVersion'), int) or not detail.get('download', {}).get('id'):
        raise CSSError(f'Theme Store download metadata incomplete: {name}')
    return detail


def _live_theme(themes, name):
    matches = [t for t in themes if _key(name) in {_key(t['name']), _key(t.get('display_name', ''))}]
    if len(matches) > 1:
        raise CSSError(f'Ambiguous loaded CSS component: {name}')
    return matches[0] if matches else None


def _color_role(label):
    label = label.casefold()
    if any(x in label for x in ('foreground', ' fg', 'text', 'label', 'icon', 'glyph', 'handle')):
        return 'text'
    if any(x in label for x in ('disabled', 'inactive', 'empty', 'off color')):
        return 'muted'
    if any(x in label for x in ('focus', 'highlight', 'accent', 'selected', 'enabled', 'fill', 'active', 'on color')):
        return 'pink'
    if any(x in label for x in ('background', ' bg', 'bg color', 'key color')):
        return 'panel'
    if any(x in label for x in ('border', 'outline', 'indicator', 'underline', 'separator', 'notification mark')):
        return 'cyan'
    if label.strip() in ('color', 'colour', 'custom color', 'custom colour', 'toggle color', 'volume color', 'color picker'):
        return 'pink'
    return None


def palette_plan(theme, palette, named_presets=None):
    """Use only controls and option values actually advertised by this backend.

    Prefer supported solid colors for readable dark panels; use pink/violet/cyan
    gradients on focus/highlight surfaces. Unknown active controls stop convergence.
    """
    plan = {}
    for patch in theme['patches']:
        colors = [c for c in patch.get('components', []) if c.get('type') == 'color-picker']
        if not colors:
            # Older themes expose named color presets instead of color pickers.
            if any(word in patch['name'].casefold() for word in ('color', 'colour')):
                options_by_name = {str(v).casefold(): v for v in patch.get('options', [])}
                choice = next((options_by_name[v] for v in (named_presets or ('pink', 'magenta', 'purple', 'violet', 'cyan')) if v in options_by_name), None)
                if choice is not None:
                    plan[patch['name']] = {'value': choice, 'components': {}}
                elif named_presets is not None and set(options_by_name).intersection(
                        {'pink', 'magenta', 'purple', 'violet', 'cyan', 'blue', 'teal', 'aqua',
                         'grey', 'gray', 'white', 'silver', 'black', 'red', 'green', 'yellow', 'orange'}):
                    raise CSSError(f"{theme['name']}/{patch['name']}: no named color matching the selected palette; choose another palette or deselect this component")
            continue
        options = patch.get('options', [])
        activators = list(dict.fromkeys(c['on'] for c in colors if c.get('on') in options))
        if not activators:
            raise CSSError(f"{theme['name']}/{patch['name']}: color control has no valid activating option")
        focus = any(x in patch['name'].casefold() for x in ('focus', 'highlight', 'slider fill'))
        preferred = ['H-Linear Grad', 'Gradient', 'Solid Color', 'Solid Colors', 'Custom', '_'] if focus else ['Solid Color', 'Solid Colors', 'Custom', '_']
        value = next((x for x in preferred if x in activators), activators[0])
        components = {}
        gradient = 'grad' in value.casefold()
        for c in colors:
            if c['on'] != value:
                continue
            role = _color_role(patch['name']) or _color_role(c['name'])
            if gradient:
                number = re.search(r'(\d+)\s*$', c['name'])
                role = ('pink', 'violet', 'cyan')[(int(number[1]) - 1) % 3] if number else role
            if role is None:
                raise CSSError(f"Unmapped color control {theme['name']}/{patch['name']}/{c['name']}; no value guessed")
            components[c['name']] = palette[role]
        plan[patch['name']] = {'value': value, 'components': components}
    return plan


def _matches_config(config, desired):
    if config.get('active') is not True:
        return False
    for name, expected in desired.items():
        current = config.get(name)
        if not expected['components'] and isinstance(current, str):
            if current != expected['value']:
                return False
            continue
        if not isinstance(current, dict) or current.get('value') != expected['value']:
            return False
        if any(current.get('components', {}).get(k, '').casefold() != v.casefold() for k, v in expected['components'].items()):
            return False
    return True


def _saved_config(theme_path, plan):
    candidates = []
    for name in ('config_ROOT.json', 'config_USER.json'):
        path = theme_path / name
        if path.is_file():
            try:
                if _matches_config(_read(path), plan):
                    candidates.append(path)
            except (OSError, ValueError, AttributeError):
                pass
    if not candidates:
        raise CSSError(f'CSS Loader did not persist the requested configuration for {theme_path.name}')
    return max(candidates, key=lambda p: p.stat().st_mtime_ns)


def _verify_live(theme, plan):
    if theme.get('enabled') is not True:
        raise CSSError(f"CSS Loader did not enable {theme['name']}")
    patches = {p['name']: p for p in theme['patches']}
    for name, expected in plan.items():
        patch = patches.get(name, {})
        components = {c['name']: c.get('value') for c in patch.get('components', [])}
        if patch.get('value') != expected['value'] or any(str(components.get(k, '')).casefold() != v.casefold() for k, v in expected['components'].items()):
            raise CSSError(f"CSS Loader did not apply {theme['name']}/{name}")


def _migrate_legacy():
    """Quarantine only a byte-identical v0.2.18 theme, preserving config and edits."""
    legacy = THEMES_DIR / 'Bubble Gum Rave'
    if not legacy.exists():
        return
    hashes = _read(core.ROOT / 'modules/decky/legacy-theme-hashes.json')
    if legacy.is_symlink() or any(not (legacy / n).is_file() or hashlib.sha256((legacy / n).read_bytes()).hexdigest() != h for n, h in hashes.items()):
        raise CSSError('Legacy Bubble Gum Rave theme has local edits; preserve/move that folder before applying the new palette')
    backup = core.STATE / 'css-legacy-backups' / str(time.time_ns())
    backup.mkdir(parents=True)
    shutil.move(str(legacy), str(backup / legacy.name))
    print(f'Preserved the obsolete v0.2.18 theme at {backup}')


def _manifest_hash():
    raw = STACK_PATH.read_bytes()
    if (core.CONFIG_HOME/'css-selection.json').exists():
        raw += json.dumps(sorted(selection())).encode()
    palette = _stack(unfiltered=True)
    raw += json.dumps({key: palette[key] for key in ('palette', 'palette_name', 'named_presets', 'preset', 'apply_palette')}, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def selection_error():
    requested = core.load_json(core.CONFIG_HOME/'appearance.json', {}).get('css') is True
    if requested and not selection():
        return 'Game Mode theming is enabled but no CSS components are selected. Choose components or turn Game Mode theming off.'
    return None


def readiness():
    """Read-only, persisted-state verification; never treats a receipt alone as proof."""
    try:
        stack = _stack()
        if selection_error(): return False, selection_error()
        if not stack['required'] and not stack['recommended']:
            return True, 'No CSS components selected; existing themes are unchanged'
        if not core._decky_loader_present():
            return False, 'Decky Loader is missing'
        plugin = core._decky_installed_plugins().get('SDH-CssLoader', {})
        if not plugin.get('valid') or plugin.get('name') != 'CSS Loader':
            return False, 'CSS Loader is missing or incomplete'
        if (core.STATE / 'ui-safe.json').exists():
            return False, 'UI safe mode is active'
        if (THEMES_DIR / 'Bubble Gum Rave').exists():
            return False, 'Legacy standalone theme still needs migration'
        receipt = _read(RECEIPT)
        if receipt.get('manifest_sha256') != _manifest_hash():
            return False, 'CSS palette has not been reconciled with this release'
        entries = receipt.get('components', {})
        for item in stack['required'] + stack['recommended']:
            entry = entries.get(item['name'])
            if not entry:
                return False, 'Component not configured: ' + item['name']
            relative = Path(entry['directory'])
            if relative.is_absolute() or len(relative.parts) != 1 or relative.name in ('.', '..'):
                return False, 'Invalid CSS receipt path'
            theme_path = THEMES_DIR / relative
            if theme_path.is_symlink() or hashlib.sha256((theme_path / 'theme.json').read_bytes()).hexdigest() != entry['manifest_sha256']:
                return False, 'Component changed: ' + item['name']
            filename = entry['config_file']
            if filename not in ('config_ROOT.json', 'config_USER.json'):
                return False, 'Invalid CSS configuration reference'
            if not _matches_config(_read(theme_path / filename), entry['patches']):
                return False, 'Palette or enabled-state drift: ' + item['name']
        profile = THEMES_DIR / (stack['preset'] + '.profile')
        if hashlib.sha256((profile / 'theme.json').read_bytes()).hexdigest() != receipt['profile_sha256']:
            return False, 'Native CSS profile changed or is missing'
        return True, f"{len(entries)} components and {stack['palette_name']} palette verified"
    except (OSError, ValueError, KeyError, TypeError, AttributeError, CSSError) as exc:
        return False, f'CSS configuration incomplete: {exc}'


def component_ready(name):
    if (core.STATE/'ui-safe.json').exists(): return False
    try:
        receipt = _read(RECEIPT)
        if receipt.get('manifest_sha256') != _manifest_hash(): return False
        entry = receipt.get('components', {}).get(name)
        if not entry: return False
        relative = Path(entry['directory'])
        if relative.is_absolute() or len(relative.parts) != 1 or relative.name in ('.', '..'): return False
        path = THEMES_DIR/relative
        if path.is_symlink() or entry['config_file'] not in ('config_ROOT.json', 'config_USER.json'): return False
        return (hashlib.sha256((path/'theme.json').read_bytes()).hexdigest() == entry['manifest_sha256']
                and _matches_config(_read(path/entry['config_file']), entry['patches']))
    except (OSError, ValueError, KeyError, TypeError): return False


def apply(only=None):
    try:
        if selection_error(): raise CSSError(selection_error())
        if (core.STATE / 'ui-safe.json').exists():
            raise CSSError('UI safe mode is active; restore it before applying CSS')
        if only is not None and only not in selection(): raise ValueError('CSS component is not selected')
        if only is not None and component_ready(only): return 0
        ok, reason = readiness()
        if ok:
            print(('UNCHANGED' if not selection() else 'READY') + ' — ' + reason)
            return 0
        if not core._decky_loader_present():
            raise CSSError('Install Decky Loader first')
        stack = _stack()
        receipt = {'schema_version': 1, 'manifest_sha256': _manifest_hash(), 'components': {}}
        previous = core.load_json(RECEIPT, {})
        if only is not None and previous.get('manifest_sha256') == receipt['manifest_sha256']:
            receipt['components'] = previous.get('components', {})
        with _backend_session() as backend:
            _migrate_legacy()
            backend.call('reset')
            themes = backend.themes()
            selected = stack['required'] + stack['recommended']
            if only is not None: selected = [item for item in selected if item['name'] == only]
            failures = []
            for item in selected:
                try:
                    name = item['name']
                    theme = _live_theme(themes, name)
                    store_id = None
                    if theme is None:
                        detail = _resolve_store_theme(name)
                        if detail['manifestVersion'] > backend.call('get_backend_version'):
                            raise CSSError(f'{name} requires a newer CSS Loader')
                        store_id = detail['id']
                        print('Installing from CSS Loader Theme Store: ' + name, flush=True)
                        backend.call('download_theme_from_url', id=store_id, url=STORE_API)
                        backend.call('reset')
                        themes = backend.themes()
                        theme = _live_theme(themes, name)
                        if theme is None:
                            raise CSSError('Theme Store download did not install ' + name)
                    plan = palette_plan(theme, stack['palette'], stack['named_presets']) if item.get('configure_palette') else {}
                    if item.get('configure_palette') and not plan:
                        if name.startswith('Chromahon') or name == 'Focus Highlight Color':
                            raise CSSError(f'{name} exposes no supported palette controls')
                        print(name + ': no color-picker controls; preserving vendor defaults')
                    for patch_name, value in item.get('patch_options', {}).items():
                        patch = next((p for p in theme['patches'] if p['name'] == patch_name), None)
                        if patch is None or value not in patch.get('options', []):
                            raise CSSError(f'{name}/{patch_name}: requested option {value!r} is unavailable')
                        if patch_name in plan:
                            raise CSSError(f'{name}/{patch_name}: conflicting palette and option settings')
                        plan[patch_name] = {'value': value, 'components': {}}
                    for patch_name, desired in plan.items():
                        current = next(p for p in theme['patches'] if p['name'] == patch_name)
                        if current.get('value') != desired['value']:
                            backend.call('set_patch_of_theme', themeName=theme['name'], patchName=patch_name, value=desired['value'])
                        live_components = {c['name']: c.get('value') for c in current.get('components', [])}
                        for component, value in desired['components'].items():
                            if str(live_components.get(component, '')).casefold() != value.casefold():
                                backend.call('set_component_of_theme_patch', themeName=theme['name'], patchName=patch_name, componentName=component, value=value)
                    if not theme.get('enabled'):
                        backend.call('set_theme_state', name=theme['name'], state=True, set_deps=True, set_deps_value=False)
                    themes = backend.themes()
                    theme = _live_theme(themes, name)
                    _verify_live(theme, plan)
                    installed = _find(_installed_themes(), name)
                    if not installed:
                        raise CSSError('Component missing on disk: ' + name)
                    config = _saved_config(installed['path'], plan)
                    receipt['components'][name] = {'directory': installed['path'].name, 'native_name': theme['name'], 'manifest_sha256': hashlib.sha256((installed['path'] / 'theme.json').read_bytes()).hexdigest(), 'config_file': config.name, 'patches': plan, 'store_id': store_id}
                    print('Verified: ' + name, flush=True)
                except (OSError, ValueError, KeyError, TypeError, CSSError) as exc:
                    failures.append(f"{item['name']}: {exc}")
                    print(f"CSS component pending: {item['name']}: {exc}", flush=True)
            if failures:
                raise CSSError('Incomplete components:\n  ' + '\n  '.join(failures))
            if only is not None:
                core.save_json(RECEIPT, receipt)
                return 0 if component_ready(only) else 2
            # Capture only the managed stack, never unrelated active third-party themes.
            profile = THEMES_DIR / (stack['preset'] + '.profile')
            if profile.exists():
                backup = core.STATE / 'css-profile-apply' / str(time.time_ns())
                backup.mkdir(parents=True)
                shutil.copytree(profile, backup / profile.name)
            backend.call('generate_preset_theme_from_theme_names', name=stack['preset'], themeNames=[e['native_name'] for e in receipt['components'].values()])
            profile_data = _read(profile / 'theme.json')
            deps = profile_data.get('dependencies', {})
            if 'PRESET' not in profile_data.get('flags', []) or set(deps) != {e['native_name'] for e in receipt['components'].values()}:
                raise CSSError('CSS Loader did not create the requested native profile')
            for entry in receipt['components'].values():
                if not _matches_config({'active': True, **deps[entry['native_name']]}, entry['patches']):
                    raise CSSError('Native CSS profile does not contain the requested palette')
            receipt['profile_sha256'] = hashlib.sha256((profile / 'theme.json').read_bytes()).hexdigest()
            backend.call('reset')
            for name, entry in receipt['components'].items():
                theme = _live_theme(backend.themes(), name)
                if theme is None:
                    raise CSSError('Component disappeared after reload: ' + name)
                _verify_live(theme, entry['patches'])
        core.save_json(RECEIPT, receipt)
        ok, reason = readiness()
        if not ok:
            raise CSSError(reason)
        from . import reliability
        if reliability.css_profile_capture(stack['preset']) != 0:
            raise CSSError('Native profile was created but recovery capture failed')
        print('READY — ' + reason)
        return 0
    except (OSError, ValueError, KeyError, TypeError, CSSError) as exc:
        print(f'CSS CONFIG_REQUIRED: {exc}')
        print('Retry in Desktop Mode: deckctl decky css apply. Completed components are retained.')
        return 2


def palette_status():
    """Report saved intent separately from verified Game Mode configuration."""
    stack = _stack()
    count = len(stack['required']) + len(stack['recommended'])
    selected = next(item['name'] for item in palette_catalog() if item['id'] == palette_id())
    if selection_error():
        state, message = 'INVALID', selected + ' selected · ' + selection_error()
    elif not count:
        state, message = 'NO_TARGETS', selected + ' selected · not applied to Game Mode. No CSS components selected; existing theme colors are unchanged.'
    elif not stack.get('apply_palette', True):
        state, message = 'PRESERVED', selected + ' selected · Game Mode recoloring is off. Existing theme colors are preserved.'
    else:
        ready, reason = readiness()
        state = 'VERIFIED' if ready else 'UNVERIFIED'
        message = selected + (' · saved palette verified for selected CSS components.' if ready else ' selected · Game Mode application not verified. ' + reason)
    return {'selectedPalette':selected, 'componentCount':count, 'state':state, 'message':message}


def status():
    ok, reason = readiness()
    palette = palette_status()
    print(('UNCHANGED' if palette['state'] in ('NO_TARGETS','PRESERVED') else 'READY' if ok else 'CONFIG_REQUIRED') + ' — ' + reason)
    print(palette['message'])
    installed = _installed_themes()
    for section in ('required', 'recommended', 'optional'):
        for item in _stack()[section]:
            present = _find(installed, item['name']) is not None
            print(f"{'PRESENT' if present else 'OPTIONAL' if section == 'optional' else 'MISSING':<10} {item['name']}")
    print(_stack()['palette_name'] + ' is the selected palette/profile, not a Theme Store package.')
    return 0 if ok else 2


def guide(write_desktop=False):
    print('CSS Loader is installed through the existing Decky plugin installer.\n'
          'Guided setup installs the required/recommended Theme Store components,\n'
          'configures their supported color controls, verifies saved state, and captures\n'
          f"a native {_stack()['preset']} profile for recovery.\n"
          'Retry: deckctl decky css apply | Audit: deckctl decky css status\n'
          'Optional layout components stay opt-in in CSS Loader.\n'
          'Gaming Mode artwork belongs to SteamGridDB; Desktop icons are independent.')
    return 0
