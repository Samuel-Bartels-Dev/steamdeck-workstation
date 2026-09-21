#!/usr/bin/env python3
"""Selection and execution boundaries for the native setup app."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'lib'))
from deckctl import core, apps, setup_builder, setup_window, gaming_options, provisioning, css_stack


class SetupWindow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        for name in ('CONFIG_HOME', 'STATE'):
            p = patch.object(core, name, self.home/name)
            p.start(); self.addCleanup(p.stop)

    def test_app_selection_includes_owning_module_and_dependencies(self):
        session = setup_window.Session()
        result = session.save({'modules': ['base'], 'apps': ['zed']})
        self.assertIn('dev', result['modules'])
        self.assertEqual(apps.selection(), ['zed'])
        self.assertIn('base', core.enabled_modules())

    def test_unknown_options_do_not_write_preferences(self):
        for payload in ({'modules': ['no-such-module'], 'apps': []},
                        {'modules': ['base'], 'apps': ['no-such-app']}):
            with self.assertRaises(ValueError):
                setup_window.Session().save(payload)
        self.assertFalse(core.CONFIG_HOME.exists())

    def test_app_save_failure_rolls_back_both_selections(self):
        setup_builder.save_plan(['base'], [])
        before = {p.name: p.read_bytes() for p in core.CONFIG_HOME.iterdir()}
        with patch.object(apps, 'save', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                setup_builder.save_plan(['base', 'terminal'], ['zed'])
        self.assertEqual(before, {p.name: p.read_bytes() for p in core.CONFIG_HOME.iterdir()})

    def test_nested_choices_persist_and_skip_unselected_setup(self):
        setup_window.Session().save({'modules': ['gaming', 'decky'], 'apps': [],
                                     'launchers': ['protonplus'], 'plugins': []})
        self.assertEqual(gaming_options.selection(), ['protonplus'])
        self.assertEqual(core._decky_selected_folders(), set())
        for key in ('heroic', 'battlenet'):
            self.assertFalse(provisioning.selected({'id': key, 'module': 'gaming'}, {'gaming'}))
        self.assertTrue(provisioning.selected({'id': 'decky', 'module': 'decky'}, {'decky'}))
        with patch.object(core, '_decky_manifest', return_value={'schema_version': 99, 'selection_upgrades': [
                {'manifest_schema_version': 99, 'add_folders': ['unwanted']}]}):
            core._decky_upgrade_selection()
            self.assertEqual(core._decky_selected_folders(), set())

    def test_invalid_nested_choices_leave_all_preferences_unchanged(self):
        for extra in ({'launchers': ['unknown']}, {'plugins': ['unknown']}, {'plugins': 'CSSLoader'}):
            with self.assertRaises(ValueError):
                setup_window.Session().save({'modules': ['base'], 'apps': [], **extra})
        self.assertFalse(core.CONFIG_HOME.exists())

    def test_last_selection_write_failure_rolls_back_entire_plan(self):
        setup_builder.save_plan(['base'], [], [], [])
        before = {p.name: p.read_bytes() for p in core.CONFIG_HOME.iterdir()}
        save = core.save_json
        def fail(path, data):
            if path.name == 'decky-selection.json': raise OSError('disk full')
            return save(path, data)
        with patch.object(core, 'save_json', side_effect=fail):
            with self.assertRaises(OSError):
                setup_builder.save_plan(['gaming'], [], ['heroic'], [])
        self.assertEqual(before, {p.name: p.read_bytes() for p in core.CONFIG_HOME.iterdir()})

    def test_css_selection_filters_defaults_and_accepts_optional_components(self):
        stack=css_stack._stack(unfiltered=True)
        optional=stack['optional'][0]['name']
        setup_builder.save_plan(['decky'], [], [], ['SDH-CssLoader'], [optional])
        effective=css_stack._stack()
        self.assertEqual([item['name'] for item in effective['required']], [optional])
        self.assertEqual(effective['recommended'], [])
        first_hash=css_stack._manifest_hash()
        setup_builder.save_plan(['decky'], [], [], ['SDH-CssLoader'], [])
        self.assertNotEqual(first_hash, css_stack._manifest_hash())
        with patch.object(css_stack, '_backend_session', side_effect=AssertionError('No backend should start')):
            self.assertTrue(css_stack.readiness()[0])
            self.assertEqual(css_stack.apply(), 0)

    def test_unknown_css_component_rejected_before_saving(self):
        with self.assertRaises(ValueError):
            setup_builder.save_plan(['decky'], [], [], [], ['unknown-theme'])
        self.assertFalse(core.CONFIG_HOME.exists())

    def test_every_curated_choice_has_an_explanatory_blurb(self):
        descriptions=core.load_json(core.ROOT/'config/setup-copy.json', {})
        snapshot=setup_window.Session().snapshot()
        sections={key:snapshot[key] for key in ('apps','launchers','plugins','css')}
        sections['modules']=[item for group in snapshot['groups'] for item in group['modules']]
        sections['components']=[item for items in snapshot['components'].values() for item in items]
        for section, items in sections.items():
            self.assertEqual(set(descriptions[section]), {item['id'] for item in items}, section)
            for item in items:
                self.assertEqual(item['summary'], descriptions[section][item['id']])
                self.assertGreater(len(item['summary']), 35, (section,item['id']))
                self.assertLess(len(item['summary']), 200, (section,item['id']))

    def test_plan_only_never_starts_installer(self):
        session = setup_window.Session(plan_only=True)
        session.save({'modules': ['base'], 'apps': []})
        with patch.object(setup_window.subprocess, 'Popen') as popen:
            with self.assertRaises(ValueError):
                session.start('install')
            popen.assert_not_called()

    def test_active_install_prevents_overlapping_run_and_plan_changes(self):
        session = setup_window.Session()
        session.selected = ['base']
        session.process = Mock()
        session.process.poll.return_value = None
        with self.assertRaises(ValueError): session.start('install')
        with self.assertRaises(ValueError): session.save({'modules': ['base'], 'apps': []})

    def test_prior_release_receipt_is_not_current_installation_progress(self):
        core.save_json(core.STATE/'provisioning.json', {'modules': {'base': {'version': 'old-release', 'status': 'READY'}}})
        session = setup_window.Session()
        session.selected = ['base']
        self.assertEqual(session.progress()['modules'][0]['status'], 'PENDING')

    def test_cli_unknown_module_does_not_silently_become_base_only(self):
        with self.assertRaises(ValueError):
            setup_builder.configure_defaults(module_names=['misspelled'], app_names=[])
        self.assertFalse(core.CONFIG_HOME.exists())

    def test_launch_only_accepts_fixed_operations(self):
        session = setup_window.Session()
        session.save({'modules': ['base'], 'apps': []})
        with patch.object(setup_window.shutil, 'which', return_value='/usr/bin/konsole'), patch.object(setup_window.subprocess, 'Popen') as popen:
            with self.assertRaises(ValueError): session.start('arbitrary shell command')
            popen.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
