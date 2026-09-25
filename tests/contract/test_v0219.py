#!/usr/bin/env python3
"""v0.2.19 behavioral tests; isolated HOME, no vendor installs or service changes."""
from __future__ import annotations
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'lib'))
from deckctl import core, css_stack as css, decky_installer, desktop, reliability, workspace

FIXTURES = ROOT / 'tests/fixtures/css'


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def upstream_themes():
    return [json.loads(p.read_text()) for p in sorted(FIXTURES.glob('steamDeckThemes*.json'))]


def component(name, patch_name='Background'):
    return {'name': name, 'display_name': name, 'enabled': False, 'patches': [
        {'name': patch_name, 'value': 'Default', 'options': ['Default', 'Custom'], 'components': [
            {'name': 'Color', 'type': 'color-picker', 'on': 'Custom', 'value': '#000000'}]}]}


class NativeBackend:
    """Simulates the published native API and its real per-theme config layout."""
    def __init__(self):
        known = {t['display_name']: t for t in upstream_themes()}
        focus = json.loads((FIXTURES / 'focus-highlight.json').read_text())
        known[focus['name']] = focus
        self.available = {}
        self.loaded = {}
        self.calls = []
        for item in css._stack()['required'] + css._stack()['recommended']:
            t = known.get(item['name']) or (component(item['name']) if item['configure_palette'] else {'name': item['name'], 'display_name': item['name'], 'enabled': False, 'patches': []})
            self.available[item['name']] = copy.deepcopy(t)

    def themes(self):
        return copy.deepcopy(list(self.loaded.values()))

    def persist(self, theme):
        root = css.THEMES_DIR / theme['name']
        if not (root / 'theme.json').exists():
            write_json(root / 'theme.json', {'name': theme['name'], 'display_name': theme['display_name'], 'manifest_version': 9, 'version': 'fixture'})
        config = {'active': theme['enabled']}
        for p in theme['patches']:
            config[p['name']] = {'value': p['value'], 'components': {c['name']: c['value'] for c in p['components']}} if p['components'] else p['value']
        write_json(root / 'config_USER.json', config)

    def call(self, method, **args):
        self.calls.append((method, copy.deepcopy(args)))
        if method == 'get_backend_version': return 9
        if method == 'get_themes': return self.themes()
        if method == 'fetch_theme_path': return str(css.THEMES_DIR)
        if method == 'reset': return {'fails': []}
        if method == 'download_theme_from_url':
            if args['url'] != css.STORE_API: raise AssertionError('Non-Store source')
            t = copy.deepcopy(self.available[args['id']]); self.loaded[t['name']] = t; self.persist(t)
        elif method == 'set_theme_state':
            t = self.loaded[args['name']]; t['enabled'] = args['state']; self.persist(t)
        elif method in ('set_patch_of_theme', 'set_component_of_theme_patch'):
            t = self.loaded[args['themeName']]; p = next(p for p in t['patches'] if p['name'] == args['patchName'])
            if method == 'set_patch_of_theme':
                if args['value'] not in p['options']: raise AssertionError('Unknown option')
                p['value'] = args['value']
            else:
                c = next(c for c in p['components'] if c['name'] == args['componentName'])
                c['value'] = args['value']
            self.persist(t)
        elif method == 'generate_preset_theme_from_theme_names':
            deps = {}
            for name in args['themeNames']:
                cfg = json.loads((css.THEMES_DIR / name / 'config_USER.json').read_text()); cfg.pop('active')
                deps[name] = cfg
            write_json(css.THEMES_DIR / (args['name'] + '.profile') / 'theme.json', {'name': args['name'] + '.profile', 'display_name': args['name'], 'flags': ['PRESET'], 'dependencies': deps})
        else: raise AssertionError('Unexpected method ' + method)
        return {'success': True}


class Isolated(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.stack = contextlib.ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(os.environ, {'HOME': str(self.home), 'DECKCTL_STATE': str(self.home / 'state'), 'DECKCTL_CONFIG': str(self.home / 'config')}))
        for module, name, value in [
            (core, 'STATE', self.home / 'state'), (core, 'CONFIG_HOME', self.home / 'config'),
            (css, 'THEMES_DIR', self.home / 'homebrew/themes'), (css, 'PLUGIN_DIR', self.home / 'homebrew/plugins/SDH-CssLoader'), (css, 'RECEIPT', self.home / 'config/css-stack-receipt.json'),
            (reliability, 'CSS_DIR', self.home / 'homebrew/themes'), (reliability, 'CSS_SNAPSHOTS', self.home / 'config/css-profiles'), (reliability, 'UI_SAFE_STATE', self.home / 'state/ui-safe.json'),
        ]: self.stack.enter_context(patch.object(module, name, value))
        core.STATE.mkdir(); core.CONFIG_HOME.mkdir()
        self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))

    def fake_install(self):
        self.stack.enter_context(patch.object(core, '_decky_loader_present', return_value=True))
        write_json(css.PLUGIN_DIR / 'plugin.json', {'name': 'CSS Loader'})
        write_json(css.PLUGIN_DIR / 'package.json', {'version': 'fixture'})
        (css.PLUGIN_DIR / 'dist').mkdir()
        (css.PLUGIN_DIR / 'dist/index.js').write_text('// test fixture')
        backend = NativeBackend()
        self.stack.enter_context(patch.object(css, '_backend_session', side_effect=lambda: contextlib.nullcontext(backend)))
        self.stack.enter_context(patch.object(css, '_resolve_store_theme', side_effect=lambda name: {'id': name, 'manifestVersion': 9}))
        return backend


class CSSBehavior(Isolated):
    def test_native_store_install_state_profile_and_second_run_noop(self):
        backend = self.fake_install()
        self.assertEqual(css.apply(), 0)
        expected = css._stack()['required'] + css._stack()['recommended']
        downloads = [args['id'] for method, args in backend.calls if method == 'download_theme_from_url']
        self.assertEqual(set(downloads), {x['name'] for x in expected})
        self.assertNotIn('Bubble Gum Rave', downloads)
        self.assertFalse((css.THEMES_DIR / 'Bubble Gum Rave').exists())
        self.assertTrue(css.readiness()[0])
        profile = reliability.CSS_SNAPSHOTS / 'Bubble Gum Rave - Base.profile/theme.json'
        self.assertTrue(profile.is_file())
        deps = json.loads(profile.read_text())['dependencies']
        self.assertEqual(len(deps), len(expected))
        calls = copy.deepcopy(backend.calls)
        before = {p: p.stat().st_mtime_ns for p in css.THEMES_DIR.rglob('*') if p.is_file()}
        self.assertEqual(css.apply(), 0)
        self.assertEqual(calls, backend.calls)
        self.assertEqual(before, {p: p.stat().st_mtime_ns for p in before})

    def test_false_api_success_cannot_pass_actual_state_verification(self):
        backend = self.fake_install()
        real = backend.call
        def call(method, **args):
            if method == 'set_component_of_theme_patch': return {'success': True}
            return real(method, **args)
        backend.call = call
        self.assertEqual(css.apply(), 2)
        self.assertFalse(css.RECEIPT.exists())
        self.assertFalse(css.readiness()[0])

    def test_missing_store_result_is_not_success(self):
        self.fake_install()
        with patch.object(css, '_resolve_store_theme', side_effect=css.CSSError('No exact match')):
            self.assertEqual(css.apply(), 2)
        self.assertFalse(css.RECEIPT.exists())

    def test_disk_drift_breaks_readiness_and_rerun_repairs(self):
        backend = self.fake_install(); self.assertEqual(css.apply(), 0)
        first = next(iter(backend.loaded.values()))
        first['enabled'] = False; backend.persist(first)
        self.assertFalse(css.readiness()[0])
        self.assertEqual(css.apply(), 0)
        self.assertTrue(css.readiness()[0])
        self.assertEqual(sum(m == 'download_theme_from_url' for m, _ in backend.calls), len(backend.loaded))

    def test_live_success_without_saved_state_is_rejected(self):
        backend = self.fake_install()
        persist = backend.persist
        def stale(t):
            persist(t)
            if t['enabled']:
                (css.THEMES_DIR / t['name'] / 'config_USER.json').write_text('{"active":false}')
        backend.persist = stale
        self.assertEqual(css.apply(), 2)
        self.assertFalse(css.RECEIPT.exists())

    def test_status_is_read_only_and_receipt_alone_is_not_proof(self):
        self.fake_install(); self.assertEqual(css.apply(), 0)
        before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.home.rglob('*') if p.is_file()}
        self.assertEqual(css.status(), 0)
        self.assertEqual(before, {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.home.rglob('*') if p.is_file()})
        next(css.THEMES_DIR.glob('*/config_USER.json')).unlink()
        self.assertFalse(css.readiness()[0])

    def test_safe_mode_not_silently_undone(self):
        self.fake_install(); self.assertEqual(css.apply(), 0)
        self.assertEqual(reliability.ui_safe(minimal=True), 0)
        self.assertFalse(css.readiness()[0])
        self.assertEqual(css.apply(), 2)
        self.assertEqual(reliability.ui_restore(), 0)
        self.assertTrue(css.readiness()[0])

    def test_profile_capture_restore_preserved(self):
        self.fake_install(); self.assertEqual(css.apply(), 0)
        path = css.THEMES_DIR / 'Bubble Gum Rave - Base.profile/theme.json'
        original = path.read_bytes(); path.write_text('{}')
        self.assertFalse(css.readiness()[0])
        self.assertEqual(reliability.css_profile_restore('Bubble Gum Rave - Base'), 0)
        self.assertEqual(path.read_bytes(), original)
        self.assertTrue(css.readiness()[0])

    def test_all_real_chromahon_schemas_use_valid_controls(self):
        totals = []
        for theme in upstream_themes():
            plan = css.palette_plan(theme, css._stack()['palette']); totals.append(sum(len(x['components']) for x in plan.values()))
            patches = {p['name']: p for p in theme['patches']}
            for name, values in plan.items():
                p = patches[name]; self.assertIn(values['value'], p['options'])
                for component_name, value in values['components'].items():
                    c = next(c for c in p['components'] if c['name'] == component_name)
                    self.assertEqual(c['on'], values['value']); self.assertEqual(c['type'], 'color-picker')
                    self.assertRegex(value, r'^#[0-9a-fA-F]{6}$')
        self.assertEqual(sorted(totals), [19, 28, 30, 30])

    def test_named_color_dropdowns_use_real_option_and_saved_scalar(self):
        theme = {'name': 'Colored Toggles', 'enabled': True, 'patches': [{'name': 'Toggle Color', 'value': 'Pink', 'options': ['Default', 'Pink', 'Cyan'], 'components': []}]}
        plan = css.palette_plan(theme, css._stack()['palette'])
        self.assertEqual(plan, {'Toggle Color': {'value': 'Pink', 'components': {}}})
        self.assertTrue(css._matches_config({'active': True, 'Toggle Color': 'Pink'}, plan))
        self.assertFalse(css._matches_config({'active': True, 'Toggle Color': 'Default'}, plan))
        css._verify_live(theme, plan)

    def test_unknown_controls_fail_instead_of_guessed_configuration(self):
        theme = component('Test', 'Unrecognized surface')
        theme['patches'][0]['components'][0]['name'] = 'Unrecognized control'
        with self.assertRaises(css.CSSError): css.palette_plan(theme, css._stack()['palette'])
        theme['patches'][0]['components'][0]['on'] = 'Missing'
        with self.assertRaises(css.CSSError): css.palette_plan(theme, css._stack()['palette'])

    def test_missing_optional_color_support_is_explicit_and_nonblocking(self):
        backend = self.fake_install(); backend.available['DellyVolume']['patches'] = []
        self.assertEqual(css.apply(), 0)
        receipt = json.loads(css.RECEIPT.read_text())
        self.assertEqual(receipt['components']['DellyVolume']['patches'], {})

    def test_custom_legacy_theme_preserved(self):
        write_json(css.THEMES_DIR / 'Bubble Gum Rave/theme.json', {'name': 'Bubble Gum Rave', 'author': 'user'})
        with self.assertRaises(css.CSSError): css._migrate_legacy()
        self.assertTrue((css.THEMES_DIR / 'Bubble Gum Rave/theme.json').is_file())

    def test_exact_legacy_theme_quarantined_not_deleted(self):
        folder = css.THEMES_DIR / 'Bubble Gum Rave'; folder.mkdir(parents=True)
        payload = b'legacy'; (folder / 'theme.json').write_bytes(payload)
        real_read = css._read
        with patch.object(css, '_read', side_effect=lambda p: {'theme.json': hashlib.sha256(payload).hexdigest()} if p.name == 'legacy-theme-hashes.json' else real_read(p)):
            css._migrate_legacy()
        self.assertFalse(folder.exists())
        backups = list((core.STATE / 'css-legacy-backups').glob('*/Bubble Gum Rave/theme.json'))
        self.assertEqual(len(backups), 1); self.assertEqual(backups[0].read_bytes(), payload)

    def test_store_exact_identity_and_unavailable_rejected(self):
        item = {'id': 'abc', 'name': 'CapyInputs', 'displayName': 'Chromahon (Input Controls)', 'type': 'Css', 'manifestVersion': 9, 'download': {'id': 'blob'}}
        with patch.object(css, '_fetch_json', side_effect=[{'items': [item], 'total': 1}, item]) as fetch:
            self.assertEqual(css._resolve_store_theme(item['displayName'])['id'], 'abc')
            self.assertIn('/themes?', fetch.call_args_list[0].args[0])
        with patch.object(css, '_fetch_json', return_value={'items': [item, {**item, 'id': 'other'}], 'total': 2}):
            with self.assertRaises(css.CSSError): css._resolve_store_theme(item['displayName'])
        with patch.object(css, '_fetch_json', side_effect=[{'items': [item], 'total': 1}, {**item, 'disabled': True}]):
            with self.assertRaises(css.CSSError): css._resolve_store_theme(item['displayName'])

    def test_backend_rejects_error_and_malformed_schema(self):
        for envelope in ({'success': False, 'res': 'error'}, {'success': True, 'res': {'success': False}}, {'success': True, 'res': {'fails': ['bad theme']}}):
            with patch.object(css, '_fetch_json', return_value=envelope):
                with self.assertRaises(css.CSSError): css.Backend().call('reset')
        with patch.object(css, '_fetch_json', return_value={'success': True, 'res': [{'name': 'x'}]}):
            with self.assertRaises(css.CSSError): css.Backend().themes()

    def test_installed_api_validation_and_temporary_bridge_cleanup(self):
        write_json(css.PLUGIN_DIR / 'plugin.json', {'name': 'CSS Loader'})
        methods = ('get_themes', 'fetch_theme_path', 'get_backend_version', 'download_theme_from_url', 'set_theme_state', 'set_patch_of_theme', 'set_component_of_theme_patch', 'reset', 'generate_preset_theme_from_theme_names')
        (css.PLUGIN_DIR / 'main.py').write_text('\n'.join(f'async def {name}(): pass' for name in methods))
        (css.PLUGIN_DIR / 'css_server.py').write_text("HOST='127.0.0.1'\nPORT=35821\nROUTE='/req'\n")
        (css.PLUGIN_DIR / 'css_utils.py').write_text('def store_or_file_config(key): return key.upper()\n')
        css._validate_plugin()
        backend = NativeBackend()
        with patch.object(css, 'Backend', return_value=backend), patch.object(backend, 'themes', side_effect=[OSError('not started'), []]), patch.object(decky_installer, '_restart_decky', return_value=True) as restart:
            with css._backend_session(): self.assertTrue((css.THEMES_DIR / 'SERVER').exists())
            self.assertFalse((css.THEMES_DIR / 'SERVER').exists()); self.assertEqual(restart.call_count, 2)
        (css.PLUGIN_DIR / 'main.py').write_text('')
        with self.assertRaises(css.CSSError): css._validate_plugin()


class DesktopBehavior(Isolated):
    def setUp(self):
        super().setUp()
        self.stack.enter_context(patch.object(desktop, 'desktop_dir', return_value=self.home / 'Desktop'))

    def test_icons_entries_idempotency_and_steam_artwork_untouched(self):
        apps = self.home / '.local/share/applications'; apps.mkdir(parents=True)
        entry = apps / 'deck-media-netflix.desktop'
        entry.write_text('[Desktop Entry]\nType=Application\nName=Netflix\nExec=/unchanged --kiosk\nIcon=web-browser\n[Desktop Action example]\nIcon=keep-this\n')
        other = apps / 'unmanaged.desktop'; other.write_text('untouched')
        moon = apps / 'Moonlight Game Streaming.desktop'
        moon.write_text('[Desktop Entry]\nType=Application\nName=Moonlight Game Streaming\nExec=steam steam://rungameid/123\nIcon=old-artwork.ico\n')
        battle = apps / 'Battle.net.desktop'
        battle.write_text('[Desktop Entry]\nType=Application\nName=Battle.net\nExec=steam steam://rungameid/456\nIcon=old-artwork.ico\n')
        artwork = self.home / '.local/share/Steam/userdata/1/config/grid/123.png'
        artwork.parent.mkdir(parents=True); artwork.write_bytes(b'artwork-owned-by-SteamGridDB')
        vdf = artwork.parent.parent / 'shortcuts.vdf'; vdf.write_bytes(b'steam-data')
        self.assertEqual(desktop.apply(), 0)
        self.assertEqual(desktop.status(), 0)
        self.assertIn('Exec=/unchanged --kiosk', entry.read_text()); self.assertIn('Icon=keep-this', entry.read_text())
        self.assertIn(str(desktop.icon_path('netflix')), entry.read_text())
        self.assertIn(str(desktop.icon_path('moonlight')), moon.read_text())
        self.assertIn(str(desktop.icon_path('battlenet')), battle.read_text())
        self.assertIn('Exec=steam steam://rungameid/123', moon.read_text())
        self.assertIn('Exec=steam steam://rungameid/456', battle.read_text())
        self.assertEqual((self.home / 'Desktop' / moon.name).read_text(), moon.read_text())
        self.assertEqual((self.home / 'Desktop' / battle.name).read_text(), battle.read_text())
        copy_path = self.home / 'Desktop' / entry.name
        self.assertEqual(copy_path.read_bytes(), entry.read_bytes()); self.assertTrue(os.access(copy_path, os.X_OK))
        self.assertEqual(artwork.read_bytes(), b'artwork-owned-by-SteamGridDB'); self.assertEqual(vdf.read_bytes(), b'steam-data'); self.assertEqual(other.read_text(), 'untouched')
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.home.rglob('*') if p.is_file()}
        self.assertEqual(desktop.apply(), 0)
        self.assertEqual(before, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before})
        desktop.icon_path('netflix').unlink(); self.assertEqual(desktop.status(), 2)
        self.assertEqual(desktop.apply(), 0); self.assertEqual(desktop.status(), 0)

    def test_desktop_links_are_preserved_without_blocking_base(self):
        apps = self.home/'.local/share/applications'; apps.mkdir(parents=True)
        desk = self.home/'Desktop'; desk.mkdir()
        source = apps/'Battle.net.desktop'
        source.write_text('[Desktop Entry]\nExec=battlenet\nIcon=old\n')
        linked = desk/source.name; linked.symlink_to(source)
        self.assertEqual(desktop.apply(), 0)
        self.assertTrue(linked.is_symlink())
        self.assertEqual(linked.readlink(), source)
        self.assertIn(str(desktop.icon_path('battlenet')), linked.read_text())
        linked.unlink()
        personal = self.home/'personal.desktop'; personal.write_text('keep this exact content')
        linked.symlink_to(personal)
        self.assertEqual(desktop.apply(), 0)
        self.assertTrue(linked.is_symlink())
        self.assertEqual(personal.read_text(), 'keep this exact content')

    def test_svg_assets_parse_and_have_distinct_identities(self):
        import xml.etree.ElementTree as ET
        hashes = set()
        for name in desktop.ICONS:
            path = ROOT / 'modules/base/icons' / f'{name}.svg'; tree = ET.parse(path)
            self.assertTrue(tree.getroot().tag.endswith('svg')); hashes.add(hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertEqual(len(hashes), len(desktop.ICONS))

    def test_workspace_provisioning_preserves_runners_and_adds_desktop_icons(self):
        with patch.object(workspace, 'APPS', self.home / '.local/share/applications'), patch.object(workspace, 'BINDIR', self.home / '.local/share/deckctl/workspace/bin'), patch.object(workspace, '_chrome', return_value=True):
            self.assertEqual(workspace.setup(), 0)
            for sid, (_, url) in workspace.SERVICES.items():
                self.assertIn(url, (workspace.BINDIR / sid).read_text())
                self.assertTrue((self.home / 'Desktop' / f'deck-workspace-{sid}.desktop').is_file())

    def test_media_helper_preserves_kiosk_receipts_and_no_duplicate_submission(self):
        helper = self.home / '.local/share/deckctl/media'; helper.mkdir(parents=True)
        (helper / 'services.json').write_bytes((ROOT / 'modules/media/services.json').read_bytes())
        bindir = self.home / 'fake-bin'; bindir.mkdir()
        (bindir / 'flatpak').write_text('#!/bin/sh\nexit 0\n')
        (bindir / 'steamos-add-to-steam').write_text('#!/bin/sh\nprintf "%s\\n" "$1" >> "$HOME/submissions"\n')
        for p in bindir.iterdir(): p.chmod(0o755)
        env = {**os.environ, 'PATH': str(bindir) + ':' + os.environ['PATH'], 'DECKCTL_ROOT': str(ROOT)}
        for _ in range(2):
            r = subprocess.run(['bash', str(ROOT / 'modules/media/setup-media.sh'), '--all'], env=env, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len((self.home / 'submissions').read_text().splitlines()), 4)
        for sid in ('netflix', 'hulu', 'crunchyroll', 'prime-video'):
            self.assertIn('--kiosk', (helper / 'bin' / sid).read_text())
            self.assertTrue((helper / 'submitted' / sid).is_file())
            self.assertTrue((self.home / 'Desktop' / f'deck-media-{sid}.desktop').is_file())


class DeckyBehavior(Isolated):
    def test_loader_requires_real_service_output_or_executable(self):
        with patch.object(core.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'stub output', '')):
            self.assertFalse(core._decky_loader_present())
        with patch.object(core.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'enabled\n', '')):
            self.assertTrue(core._decky_loader_present())

    def test_incomplete_plugins_do_not_satisfy_guided_install(self):
        folder = self.home / 'homebrew/plugins/SDH-CssLoader'
        write_json(folder / 'plugin.json', {'name': 'CSS Loader'})
        with patch.object(core, '_decky_selected_folders', return_value={'SDH-CssLoader'}), patch.object(core, '_decky_loader_present', return_value=True):
            self.assertFalse(core._decky_selected_all_installed())
            write_json(folder / 'package.json', {'version': '1'})
            (folder / 'dist').mkdir(); (folder / 'dist/index.js').write_text('// installed payload')
            self.assertTrue(core._decky_selected_all_installed())

    def test_steamdeckdb_request_maps_to_existing_artwork_owner(self):
        items = core._decky_item_map(); grid = items['decky-steamgriddb']
        self.assertEqual(grid['name'], 'SteamGridDB'); self.assertIn('SteamDeckDB', grid['requested_aliases'])
        self.assertIn('decky-steamgriddb', core._decky_default_selection())
        self.assertNotIn('SteamDeckDB', [i['name'] for i in items.values()])

    def test_decky_zip_identity_and_traversal_rejected(self):
        zpath = self.home / 'plugin.zip'
        with zipfile.ZipFile(zpath, 'w') as z:
            z.writestr('plugin/plugin.json', '{"name":"CSS Loader"}')
            z.writestr('plugin/package.json', '{}'); z.writestr('plugin/dist/index.js', '// code')
        self.assertEqual(decky_installer._validate_zip(zpath, 'CSS Loader')[0], 'plugin')
        with self.assertRaises(decky_installer.InstallError): decky_installer._validate_zip(zpath, 'Other')
        with zipfile.ZipFile(zpath, 'a') as z: z.writestr('../escape', 'bad')
        with self.assertRaises(decky_installer.InstallError): decky_installer._validate_zip(zpath, 'CSS Loader')


class RecoveryAndSource(Isolated):
    def test_support_bundle_excludes_private_payloads_and_redacts_settings(self):
        marker = 'PRIVATE-PAYLOAD-MUST-NOT-APPEAR'
        for rel in ('Emulation/roms/game.rom', 'Emulation/bios/firmware.bin', '.ssh/id_ed25519', '.var/app/com.google.Chrome/Default/Cookies'):
            path = self.home / rel; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(marker)
        write_json(core.CONFIG_HOME / 'settings.json', {'password': marker, 'authentication': marker, 'token': marker, 'theme': 'safe-value'})
        with patch.object(core, 'detect_hardware', return_value={}), patch.object(core, 'enabled_modules', return_value=[]), patch.object(core, 'storage_health', return_value={}), patch.object(core, 'setup_state', return_value={}), patch.object(reliability.terminal, 'status_data', return_value={}), patch.object(reliability.shutil, 'which', return_value=None):
            path = reliability.support_bundle()
        with zipfile.ZipFile(path) as z:
            for name in z.namelist(): self.assertNotIn(marker.encode(), z.read(name))
            self.assertIn('safe-value', z.read('config/settings.json').decode())
            self.assertFalse(any('/roms/' in n or '/bios/' in n or '.ssh' in n or 'Cookies' in n for n in z.namelist()))

    def test_baseline_inventory_and_unchanged_subsystems(self):
        guard = json.loads((ROOT / 'tests/fixtures/baseline-v0.2.18.json').read_text())
        for name in guard['required_files']:
            self.assertTrue((ROOT / name).is_file(), name)
        reviewed = json.loads((ROOT / 'tests/fixtures/baseline-v0.2.19.json').read_text())['reviewed_changes']
        patch_changes = json.loads((ROOT / 'tests/fixtures/baseline-v0.2.21.json').read_text())['provisioning_changes']
        patch_changes += json.loads((ROOT / 'tests/fixtures/baseline-v0.2.22.json').read_text())['maintenance_changes']
        patch_changes += json.loads((ROOT / 'tests/fixtures/baseline-v0.2.23.json').read_text())['maintenance_changes']
        patch_changes += json.loads((ROOT / 'tests/fixtures/baseline-v0.2.24.json').read_text())['plugin_changes']
        patch_changes += json.loads((ROOT/'tests/fixtures/baseline-v0.2.25.json').read_text())['reliability_changes']
        for name, sha in guard['unchanged_files'].items():
            if name in reviewed or name in patch_changes: continue
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), sha, name)
        for name, mode in guard['executable_modes'].items():
            self.assertEqual((ROOT / name).stat().st_mode & 0o777, mode, name)
        self.assertEqual(set(core.module_manifests()), set(guard['modules']) | {'ai-workspace'})
        self.assertRegex((ROOT / 'VERSION').read_text().strip(), r'^0\.2\.43(?:-rc[1-9]\d*)?$')

    def test_all_shell_python_json_syntax_and_entry_permissions(self):
        import ast
        for path in ROOT.rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts: continue
            if path.suffix == '.json': json.loads(path.read_text())
            if path.suffix == '.py': ast.parse(path.read_text(), filename=str(path))
            first = path.read_bytes()[:64]
            if path.suffix == '.sh' or first.startswith(b'#!/usr/bin/env bash'):
                r = subprocess.run(['bash', '-n', str(path)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
            if first.startswith(b'#!'):
                self.assertTrue(os.access(path, os.X_OK), str(path))


if __name__ == '__main__':
    unittest.main(verbosity=2)
