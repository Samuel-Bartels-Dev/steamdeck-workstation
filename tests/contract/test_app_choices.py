#!/usr/bin/env python3
"""Selection and safe removal contracts; no real Flatpak operations."""
import argparse
import contextlib
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
sys.path.insert(0, str(ROOT / 'lib'))
from deckctl import apps, core


class Choices(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        p = patch.object(core, 'CONFIG_HOME', self.home / 'config')
        p.start(); self.addCleanup(p.stop)
        self.out = contextlib.redirect_stdout(io.StringIO())
        self.out.__enter__(); self.addCleanup(self.out.__exit__, None, None, None)
        self.installed = set()
        self.system = set()
        self.calls = []
        self.failed_app = None
        p = patch.object(apps.subprocess, 'run', side_effect=self.flatpak)
        p.start(); self.addCleanup(p.stop)

    def flatpak(self, command, **kwargs):
        self.calls.append(command)
        app_id = command[-1]
        code = 0
        if command[1] == 'info':
            scope = self.installed if '--user' in command else self.installed | self.system
            code = 0 if app_id in scope else 1
        elif command[1] == 'uninstall':
            self.assertEqual(command[2:-1], ['--user', '--app', '--no-related', '-y'])
            self.assertNotIn(app_id, self.system)
            if app_id == self.failed_app:
                code = 1
            else:
                self.installed.discard(app_id)
        elif command[1] == 'install':
            self.assertEqual(command[2:-1], ['--user', '-y', 'flathub'])
            if app_id == self.failed_app:
                code = 1
            else:
                self.installed.add(app_id)
        else:
            self.fail(command)
        return subprocess.CompletedProcess(command, code)

    def test_selection_is_readonly_until_saved_and_unknown_is_atomic(self):
        self.assertEqual(set(apps.selection()), set(apps.catalog()))
        self.assertFalse(core.CONFIG_HOME.exists())
        apps.choose(['zen', 'vlc'])
        before = (core.CONFIG_HOME / 'apps.json').read_bytes()
        with self.assertRaises(ValueError):
            apps.choose(['spotify', '--all'])
        self.assertEqual((core.CONFIG_HOME / 'apps.json').read_bytes(), before)
        self.assertEqual(apps.selection(), ['vlc', 'zen'])
        apps.choose([], none=True)
        self.assertEqual(apps.selection(), [])
        self.assertEqual(self.calls, [])

    def test_requested_apps_install_independently_and_reuse_existing(self):
        names = ['parsec', 'slack', 'whatsapp', 'telegram', 'plex']
        apps.save(names)
        for _ in range(2):
            for name in names:
                self.assertEqual(apps.module_action('install', apps.catalog()[name]['id']), 0)
        self.assertEqual(self.installed, {apps.catalog()[name]['id'] for name in names})
        self.assertEqual(sum(c[1] == 'install' for c in self.calls), len(names))

    def test_invalid_selection_never_defaults_to_installing(self):
        core.CONFIG_HOME.mkdir()
        for value in ['{', '{"selected":null}', '{"selected":["unknown"]}', '{"selected":["zen","zen"]}']:
            (core.CONFIG_HOME / 'apps.json').write_text(value)
            with self.assertRaises(ValueError):
                apps.module_action('install', apps.catalog()['zen']['id'])
        self.assertEqual(self.calls, [])

    def test_unselected_modules_skip_and_verify_without_flatpak(self):
        apps.save([])
        for item in apps.catalog().values():
            self.assertEqual(apps.module_action('install', item['id']), 0)
            self.assertEqual(apps.module_action('verify', item['id']), 0)
        self.assertEqual(self.calls, [])

    def test_uninstall_preview_preserves_everything_then_removes_only_target(self):
        spotify = apps.catalog()['spotify']['id']
        zen = apps.catalog()['zen']['id']
        self.installed.update([spotify, zen])
        settings = self.home / '.var/app' / spotify / 'config/settings'
        settings.parent.mkdir(parents=True); settings.write_text('keep me')
        apps.uninstall(['spotify'])
        self.assertFalse(core.CONFIG_HOME.exists())
        self.assertEqual(self.installed, {spotify, zen})
        self.assertEqual(apps.uninstall(['spotify'], True), 0)
        self.assertEqual(self.installed, {zen})
        self.assertNotIn('spotify', apps.selection())
        self.assertEqual(settings.read_text(), 'keep me')
        apps.module_action('install', spotify)
        self.assertNotIn(spotify, self.installed)
        self.assertEqual(apps.uninstall(['spotify'], True), 0)
        self.assertEqual(sum(c[1] == 'uninstall' for c in self.calls), 1)

    def test_system_only_and_invalid_targets_refuse_all_changes(self):
        self.system.add(apps.catalog()['zen']['id'])
        self.installed.add(apps.catalog()['spotify']['id'])
        for names in [['spotify', 'zen'], ['spotify', 'bad']]:
            with self.assertRaises(ValueError):
                apps.uninstall(names, True)
        self.assertFalse(core.CONFIG_HOME.exists())
        self.assertFalse(any(c[1] == 'uninstall' for c in self.calls))

    def test_failed_removal_stays_disabled_and_retry_succeeds(self):
        spotify = apps.catalog()['spotify']['id']
        self.installed.add(spotify); self.failed_app = spotify
        self.assertEqual(apps.uninstall(['spotify'], True), 1)
        self.assertNotIn('spotify', apps.selection())
        self.assertIn(spotify, self.installed)
        self.failed_app = None
        self.assertEqual(apps.uninstall(['spotify'], True), 0)
        self.assertNotIn(spotify, self.installed)

    def test_install_names_reenable_and_continue_after_failure(self):
        apps.save([])
        self.failed_app = apps.catalog()['zen']['id']
        args = argparse.Namespace(apps_command='install', names=['zen', 'spotify'])
        self.assertEqual(apps.dispatch(args), 1)
        self.assertEqual(set(apps.selection()), {'zen', 'spotify'})
        self.assertIn(apps.catalog()['spotify']['id'], self.installed)
        self.failed_app = None
        self.assertEqual(apps.dispatch(args), 0)

    def test_cancelled_prompt_does_not_save_partial_choices(self):
        apps.save(['zen']); before = (core.CONFIG_HOME / 'apps.json').read_bytes()
        with patch.object(sys.stdin, 'isatty', return_value=True), patch('builtins.input', side_effect=['y', EOFError()]):
            with self.assertRaises(EOFError):
                apps.choose([])
        self.assertEqual((core.CONFIG_HOME / 'apps.json').read_bytes(), before)

    def test_shell_verifiers_respect_none(self):
        apps.save([])
        env = {**os.environ, 'DECKCTL_ROOT': str(ROOT), 'DECKCTL_CONFIG': str(core.CONFIG_HOME), 'HOME': str(self.home)}
        # Use the real subprocess API for the shell integration, not the mocked Flatpak runner.
        with patch.object(apps.subprocess, 'run', side_effect=None) as mocked:
            # Popen avoids a global run mock and exercises the real shell/Python bridge.
            for module in ('utilities', 'media'):
                with subprocess.Popen(['bash', str(ROOT / 'modules' / module / 'verify.sh')], env=env,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
                    stdout, stderr = process.communicate(timeout=15)
                self.assertEqual(process.returncode, 0, stderr)
                self.assertEqual(json.loads(stdout)['status'], 'READY')
            mocked.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
