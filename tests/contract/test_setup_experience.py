#!/usr/bin/env python3
"""Portable choices, per-item dependency execution and honest preview contracts."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'lib'))
from deckctl import core, setup_plan, setup_install, setup_finish, setup_builder, setup_window, reliability, terminal


class Experience(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ('CONFIG_HOME', 'STATE'):
            handle = patch.object(core, name, self.root/name)
            handle.start(); self.addCleanup(handle.stop)
        self.plan = {'modules': ['base'], 'apps': [], 'components': {}, 'launchers': [], 'plugins': [], 'css': [], 'palette': 'ocean'}

    def test_model_adds_only_required_tools_and_chrome_is_shared(self):
        self.plan['components'] = {'ai-workspace': ['model-7b'], 'workspace': ['notion'], 'media': ['netflix']}
        _, rows = setup_plan.items(self.plan)
        keys = [row['key'] for row in rows]
        self.assertIn('terminal:opencode', keys)
        self.assertIn('ai-workspace:ollama', keys)
        self.assertNotIn('ai-workspace:model', keys)
        self.assertNotIn('terminal:tmux', keys)
        self.assertEqual(keys.count('dependency:chrome'), 1)
        for row in rows:
            for parent in row['requires']: self.assertLess(keys.index(parent), keys.index(row['key']))
        self.assertFalse(core.CONFIG_HOME.exists())

    def test_flatpak_preview_preserves_system_and_compares_user_commit(self):
        row = {'key': 'app:slack', 'kind': 'flatpak', 'flatpak': 'com.slack.Slack'}
        with patch.object(setup_plan, 'present', return_value=(True, {'scope': 'system'})), patch.object(setup_plan, 'command', side_effect=AssertionError('System package must be preserved')):
            self.assertEqual(setup_plan.inspect(row, online=True)['action'], 'PRESERVE_SYSTEM')
        with patch.object(setup_plan, 'present', return_value=(True, {'scope': 'user', 'commit': 'old'})), patch.object(setup_plan, 'command', side_effect=['new', 'Download size: 100.0 MB\nInstalled size: 250.0 MB']):
            result = setup_plan.inspect(row, online=True)
            self.assertEqual(result['action'], 'UPDATE')
            self.assertGreaterEqual(result['spaceBytes'], 350000000)
        self.assertIsNone(setup_plan._size('Download size: unknown', 'Download size'))

    def test_decky_dependency_checks_loader_not_account_or_plugins(self):
        with patch.object(core, '_decky_loader_present', return_value=True), patch.object(core, 'module_status', side_effect=AssertionError('Aggregate plugin state must not block the loader')):
            self.assertTrue(setup_plan.present({'key': 'module:decky', 'kind': 'module', 'owner': 'decky'})[0])
            setup_install._module('decky')

    def test_low_space_preview_checks_the_target_filesystem(self):
        row = dict(key='terminal:tmux', visible=True, action='NEW', spaceBytes=2*setup_plan.GIB, storagePath=str(self.root))
        with patch.object(setup_plan, 'items', return_value=(self.plan, [row])), patch.object(setup_plan, 'inspect', return_value=row), patch.object(setup_plan.shutil, 'disk_usage', return_value=type('Usage', (), {'free': setup_plan.GIB})()):
            result = setup_plan.preview(self.plan)
        self.assertFalse(result['canInstall'])
        self.assertEqual(result['volumes'][0]['requiredBytes'], 3*setup_plan.GIB)
        self.assertFalse(core.STATE.exists())

    def test_web_services_require_sign_in_and_staged_launcher_requires_setup(self):
        self.plan['components'] = {'media': ['netflix', 'hulu']}
        self.plan['launchers'] = ['nonsteamlaunchers']
        rows = {row['key']: row for row in setup_plan.items(self.plan)[1]}
        self.assertEqual(rows['media:netflix']['followup'], 'signin')
        self.assertEqual(rows['media:hulu']['followup'], 'signin')
        self.assertEqual(rows['launcher:nonsteamlaunchers']['followup'], 'setup')

    def test_offline_model_is_not_reported_up_to_date(self):
        row = {'key': 'ai-workspace:model', 'kind': 'component', 'component': 'model'}
        with patch.object(setup_plan, 'present', return_value=(True, {'model': 'qwen2.5-coder:1.5b'})), patch.object(terminal, '_request', side_effect=OSError('offline')):
            result = setup_plan.inspect(row, online=True)
        self.assertEqual(result['action'], 'INSTALLED')
        self.assertIn('Unavailable', result['updateCheck'])
        self.assertIsNone(result['downloadBytes'])
        self.assertFalse(core.STATE.exists())

    def test_failure_continues_independent_item_and_resume_checks_evidence(self):
        rows = [dict(key=key, name=key, kind='component', requires=deps) for key, deps in [('a', []), ('b', ['a']), ('c', [])]]
        calls = []
        def execute(row):
            calls.append(row['key'])
            if row['key'] == 'a': raise RuntimeError('failed')
        with patch.object(setup_plan, 'items', return_value=(self.plan, rows)), patch.object(setup_plan, 'storage_budget', return_value=(self.root, None, '')), patch.object(setup_install, 'execute', side_effect=execute), patch.object(setup_install, 'verify', return_value=True):
            self.assertEqual(setup_install.run(), 1)
        state = setup_install.snapshot()['items']
        self.assertEqual(calls, ['a', 'c'])
        self.assertEqual(state['b']['status'], 'BLOCKED')
        self.assertEqual(state['c']['status'], 'DONE')
        calls.clear()
        with patch.object(setup_plan, 'items', return_value=(self.plan, rows)), patch.object(setup_plan, 'storage_budget', return_value=(self.root, None, '')), patch.object(setup_install, 'execute', side_effect=lambda row: calls.append(row['key'])), patch.object(setup_install, 'verify', return_value=True):
            self.assertEqual(setup_install.run(only='b'), 0)
        self.assertEqual(calls, ['a', 'b'])

    def test_interrupted_state_is_read_only_and_lock_excludes_another_runner(self):
        core.save_json(setup_install.state_path(), {'items': {'a': {'status': 'RUNNING'}}})
        before = setup_install.state_path().read_bytes()
        self.assertEqual(setup_install.snapshot()['items']['a']['status'], 'INTERRUPTED')
        self.assertEqual(before, setup_install.state_path().read_bytes())
        with setup_install.lock():
            self.assertTrue(setup_install.running())
            with self.assertRaises(ValueError):
                with setup_install.lock(): pass
            with self.assertRaises(ValueError): setup_window.Session().save(self.plan)

    def test_sharing_materializes_choices_and_import_preview_does_not_write(self):
        setup_builder.save_plan(['base', 'dev'], ['slack'], [], [], [], {'dev': ['claude-code']}, 'ocean')
        with patch.object(reliability, 'CSS_DIR', self.root/'none'), patch.object(reliability, 'PROFILE_EXPORT_DIR', self.root/'exports'):
            archive = reliability.profile_export()
        current = {p.name: p.read_bytes() for p in core.CONFIG_HOME.iterdir()}
        preview = reliability.profile_import(str(archive), preview=True)
        self.assertEqual(preview['choices']['apps.json']['selected'], ['slack'])
        self.assertEqual(preview['choices']['components.json']['dev'], ['claude-code'])
        self.assertEqual(preview['choices']['decky-selection.json']['selected_folders'], [])
        self.assertEqual(current, {p.name: p.read_bytes() for p in core.CONFIG_HOME.iterdir()})
        self.assertFalse((core.STATE/'profile-import-rollback').exists())
        setup_builder.save_plan(['base'], [], [], [], [], {}, 'graphite')
        reliability.profile_import(str(archive))
        self.assertEqual(core.load_json(core.CONFIG_HOME/'apps.json', {})['selected'], ['slack'])
        self.assertEqual(core.load_json(core.CONFIG_HOME/'css-selection.json', {})['palette'], 'ocean')

    def test_invalid_selector_is_rejected_and_cancel_is_read_only(self):
        for name, value in [('apps.json', {'selected': ['made-up']}), ('decky-selection.json', {'selected_folders': ['made-up']}), ('components.json', {'dev': ['made-up']})]:
            with self.assertRaises(ValueError): reliability._validate_choices(name, value)
        setup_window.Session().share('import-cancel')
        self.assertFalse(core.CONFIG_HOME.exists())

    def test_finish_never_infers_sign_in_from_package_presence(self):
        row = dict(key='app:slack', name='Slack', visible=True, kind='flatpak', owner='dev', flatpak='com.slack.Slack', followup='signin')
        with patch.object(setup_plan, 'items', return_value=(self.plan, [row])), patch.object(setup_plan, 'present', return_value=(True, {})):
            self.assertEqual(setup_finish.rows()[0]['status'], 'Needs sign-in')
            with self.assertRaises(ValueError): setup_finish.action('arbitrary', 'launch')
            setup_finish.action('app:slack', 'confirm')
            self.assertEqual(setup_finish.rows()[0]['status'], 'Ready')
            with patch.object(setup_plan, 'present', return_value=(False, {})):
                self.assertEqual(setup_finish.rows()[0]['status'], 'Needs setup')


if __name__ == '__main__': unittest.main(verbosity=2)
