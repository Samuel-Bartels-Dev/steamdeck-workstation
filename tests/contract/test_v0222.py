#!/usr/bin/env python3
"""Provisioning regressions: executable vendor stand-ins and saved native CSS state."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'lib'))
from deckctl import android, css_stack as css
from test_v0219 import Isolated, FIXTURES


class AndroidProvisioning(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.home = Path(temp.name)
        self.stack = contextlib.ExitStack(); self.addCleanup(self.stack.close)
        for name, value in {'HOME':self.home, 'CHECKOUT':self.home/'checkout',
                            'IMAGE':self.home/'Android_Waydroid/waydroid.img',
                            'STATE':self.home/'.local/share/waydroid', 'LEGACY':self.home/'waydroid',
                            'LAUNCHER':self.home/'Android_Waydroid/Android_Waydroid_Cage.sh',
                            'SHORTCUT_HELPER':self.home/'missing-shortcut-helper'}.items():
            self.stack.enter_context(patch.object(android, name, value))
        self.stack.enter_context(patch.dict(os.environ, {'HOME':str(self.home), 'DISPLAY':':fixture', 'WAYLAND_DISPLAY':'', 'DECKCTL_STATE':str(self.home/'state'), 'DECKCTL_CONFIG':str(self.home/'config')}))
        self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        android.IMAGE.parent.mkdir(); android.IMAGE.write_bytes(b'preserved image')
        self.launcher('mkdir -p "$HOME/.local/share/waydroid"\nprintf opened > "$HOME/launched"')

    def launcher(self, body):
        android.LAUNCHER.write_text('#!/usr/bin/env bash\nset -eu\n'+body+'\n')
        android.LAUNCHER.chmod(0o755)

    def test_existing_image_first_run_uses_bundled_launcher_without_repair(self):
        with patch.object(android, '_run', side_effect=AssertionError('Unexpected repair')):
            self.assertEqual(android.retry(), 0)
        self.assertTrue(android.ready())
        self.assertEqual((self.home/'launched').read_text(), 'opened')
        self.assertEqual(android.IMAGE.read_bytes(), b'preserved image')

    def test_ready_retry_and_install_do_not_launch_or_repair(self):
        android.STATE.mkdir(parents=True)
        with patch.object(android, '_run', side_effect=AssertionError()), patch.object(android, '_first_run', side_effect=AssertionError()):
            self.assertEqual(android.retry(), 0); self.assertEqual(android.install(), 0)
        self.assertFalse((self.home/'launched').exists())

    def test_launch_failure_is_not_success_even_if_state_was_created(self):
        self.launcher('mkdir -p "$HOME/.local/share/waydroid"\nexit 7')
        self.assertEqual(android.retry(), 7)

    def test_zero_exit_without_state_is_config_required(self):
        self.launcher('exit 0')
        self.assertEqual(android.retry(), 2); self.assertFalse(android.ready())

    def test_headless_first_run_is_read_only_config_required(self):
        with patch.dict(os.environ, {'DISPLAY':'', 'WAYLAND_DISPLAY':''}):
            self.assertEqual(android.retry(), 2)
        self.assertFalse((self.home/'launched').exists())

    def test_missing_launcher_routes_to_protected_repair(self):
        android.LAUNCHER.unlink()
        with patch.object(android, '_run', return_value=2) as run:
            self.assertEqual(android.retry(), 2); run.assert_called_once_with('--repair')

    def test_fresh_install_routes_to_vendor(self):
        android.IMAGE.unlink()
        with patch.object(android, '_run', return_value=0) as run:
            self.assertEqual(android.install(), 0); run.assert_called_once_with()

    def test_post_installer_first_run_with_and_without_steam_shim(self):
        android.CHECKOUT.mkdir(); (android.CHECKOUT/'.git').mkdir()
        installer = android.CHECKOUT/'steamos-waydroid-installer.sh'
        installer.write_text('#!/usr/bin/env bash\nexit 0\n'); installer.chmod(0o755)
        for helper in (None, '/usr/bin/true'):
            with self.subTest(steam_helper=helper), patch.object(android.shutil, 'which', return_value=helper):
                if android.STATE.exists(): android.STATE.rmdir()
                self.assertEqual(android._run('--repair'), 0)
                self.assertTrue(android.STATE.is_dir())

    def test_failed_vendor_install_never_launches_android(self):
        android.CHECKOUT.mkdir(); (android.CHECKOUT/'.git').mkdir()
        installer=android.CHECKOUT/'steamos-waydroid-installer.sh'
        installer.write_text('#!/usr/bin/env bash\nexit 9\n'); installer.chmod(0o755)
        with patch.object(android.shutil, 'which', return_value=None):
            self.assertEqual(android._run(), 9)
        self.assertFalse((self.home/'launched').exists())

    def test_vendor_success_without_image_does_not_claim_ready(self):
        android.IMAGE.unlink(); android.CHECKOUT.mkdir(); (android.CHECKOUT/'.git').mkdir()
        installer=android.CHECKOUT/'steamos-waydroid-installer.sh'
        installer.write_text('#!/usr/bin/env bash\nexit 0\n'); installer.chmod(0o755)
        with patch.object(android.shutil, 'which', return_value=None):
            self.assertEqual(android._run(), 2)

    def test_staged_setup_executes_persistent_deckctl_retry(self):
        env={**os.environ, 'DECKCTL_ROOT':str(ROOT)}
        subprocess.run(['bash', str(ROOT/'modules/android/install.sh')], env=env, check=True, capture_output=True)
        control=self.home/'.local/share/steamdeck-workstation/current/bin/deckctl'
        control.parent.mkdir(parents=True)
        control.write_text('#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "$HOME/argv"\nexit 7\n'); control.chmod(0o755)
        helper=self.home/'.local/share/deckctl/android/waydroid-setup.sh'
        result=subprocess.run([str(helper)], env=env)
        self.assertEqual(result.returncode, 7)
        self.assertEqual((self.home/'argv').read_text().splitlines(), ['android','retry'])


class CSSProvisioning(unittest.TestCase):
    setUp = Isolated.setUp
    fake_install = Isolated.fake_install

    def test_entire_requested_selection_is_enabled_and_profiled(self):
        required={'Percentages','Round','Clean Gameview','Centered Game Text','Art Hero','Better Blur','Better Game Badges','Better Achievements','Clean Game Launch','Game Cover Reflections','DellyVolume','Focus Highlight Color'}
        backend=self.fake_install()
        self.assertEqual(css.apply(), 0)
        receipt=json.loads(css.RECEIPT.read_text())
        self.assertTrue(required <= set(receipt['components']))
        self.assertNotIn('Colored Toggles', receipt['components'])
        self.assertNotIn('Colored Toggles', backend.loaded)
        for name in required:
            entry=receipt['components'][name]
            saved=json.loads((css.THEMES_DIR/entry['directory']/entry['config_file']).read_text())
            self.assertTrue(saved['active'], name)
        focus=receipt['components']['Focus Highlight Color']['patches']
        self.assertEqual(focus['Round Compatibility']['value'], 'Yes')
        self.assertEqual(set(focus['Highlight Colors']['components'].values()), {css._stack()['palette']['pink']})
        profile=json.loads((css.THEMES_DIR/(css._stack()['preset']+'.profile')/'theme.json').read_text())
        self.assertTrue(required <= set(profile['dependencies']))
        before=len(backend.calls); self.assertEqual(css.apply(),0)
        self.assertEqual(len(backend.calls),before)

    def test_component_failure_does_not_skip_later_components_or_claim_ready(self):
        backend=self.fake_install()
        def resolve(name):
            if name=='Round': raise css.CSSError('Store unavailable for Round')
            return {'id':name, 'manifestVersion':9}
        with patch.object(css, '_resolve_store_theme', side_effect=resolve):
            self.assertEqual(css.apply(),2)
        self.assertTrue(backend.loaded['Focus Highlight Color']['enabled'])
        self.assertTrue(backend.loaded['Clean Game Launch']['enabled'])
        self.assertFalse(css.RECEIPT.exists()); self.assertFalse(css.readiness()[0])
        completed={n for n in backend.loaded}
        before=len(backend.calls); self.assertEqual(css.apply(),0)
        downloaded=[args['id'] for method,args in backend.calls[before:] if method=='download_theme_from_url']
        self.assertEqual(downloaded,['Round'])
        self.assertTrue(completed <= set(backend.loaded)); self.assertTrue(css.readiness()[0])

    def test_missing_round_compatibility_option_is_reported(self):
        backend=self.fake_install()
        backend.available['Focus Highlight Color']['patches'][1]['options']=['No']
        self.assertEqual(css.apply(),2); self.assertFalse(css.RECEIPT.exists())

    def test_missing_focus_color_controls_cannot_fake_palette_success(self):
        backend=self.fake_install()
        backend.available['Focus Highlight Color']['patches']=[]
        self.assertEqual(css.apply(),2); self.assertFalse(css.RECEIPT.exists())


class Preservation(unittest.TestCase):
    def test_previous_release_preserved_outside_named_patch(self):
        guard=json.loads((ROOT/'tests/fixtures/baseline-v0.2.21.json').read_text())
        changed=set()
        for name, expected in guard['files'].items():
            p=ROOT/name; self.assertTrue(p.is_file(),name)
            self.assertEqual(p.stat().st_mode & 0o777,expected['mode'],name)
            if hashlib.sha256(p.read_bytes()).hexdigest()!=expected['sha256']:changed.add(name)
        maintenance=set(json.loads((ROOT/'tests/fixtures/baseline-v0.2.22.json').read_text())['maintenance_changes'])
        maintenance.update(json.loads((ROOT/'tests/fixtures/baseline-v0.2.23.json').read_text())['maintenance_changes'])
        maintenance.update(json.loads((ROOT/'tests/fixtures/baseline-v0.2.24.json').read_text())['plugin_changes'])
        maintenance.update(json.loads((ROOT/'tests/fixtures/baseline-v0.2.25.json').read_text())['reliability_changes'])
        self.assertEqual(changed-maintenance,set(guard['provisioning_changes'])-maintenance)
        self.assertEqual((ROOT/'VERSION').read_text().strip(),'0.2.38')
        self.assertIn('tests/fixtures/baseline-v0.2.18.json',maintenance)
        for path in ('tests/fixtures/baseline-v0.2.19.json','tests/fixtures/baseline-v0.2.20.json'):
            self.assertNotIn(path,changed)

if __name__=='__main__':unittest.main(verbosity=2)
