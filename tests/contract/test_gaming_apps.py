#!/usr/bin/env python3
"""Gaming Mode integration contracts without real Flatpak or Steam operations."""
from contextlib import ExitStack
from pathlib import Path
import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'lib'))
from deckctl import apps, app_shortcuts, core, setup_install, setup_plan, workspace


class GamingApps(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.home = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.stack.enter_context(patch.object(Path, 'home', return_value=self.home))
        self.stack.enter_context(patch.object(core, 'CONFIG_HOME', self.home/'config'))
        self.stack.enter_context(patch.object(core, 'STATE', self.home/'state'))
        self.stack.enter_context(patch.object(workspace, 'APPS', self.home/'applications'))
        self.stack.enter_context(patch.object(workspace, 'BINDIR', self.home/'workspace/bin'))
        self.ensure = self.stack.enter_context(patch.object(app_shortcuts, 'ensure', return_value='READY'))

    def test_fresh_installs_register_each_requested_flatpak_only_after_success(self):
        for key in sorted(apps.GAMING_KEYS):
            with self.subTest(key=key), patch.object(apps, 'has', side_effect=[False, True]), patch.object(apps.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)):
                apps.save([key])
                self.assertEqual(apps.module_action('install', apps.catalog()[key]['id']), 0)
                path = apps.gaming_desktop(key)
                self.assertIn('Exec=/usr/bin/flatpak run '+apps.catalog()[key]['id'], path.read_text())
                self.ensure.assert_called_with('app:'+key, apps.catalog()[key]['name'], path)
        self.ensure.reset_mock()
        with patch.object(apps, 'has', return_value=False), patch.object(apps.subprocess, 'run', return_value=subprocess.CompletedProcess([], 7)):
            self.assertEqual(apps.module_action('install', apps.catalog()['spotify']['id']), 7)
        self.ensure.assert_not_called()

    def test_system_install_reused_and_verify_deselection_never_submit(self):
        apps.save(['discord'])
        with patch.object(apps, 'has', side_effect=lambda app_id, scope=None: scope is None), patch.object(apps.subprocess, 'run') as run:
            self.assertEqual(apps.module_action('install', apps.catalog()['discord']['id']), 0)
            run.assert_not_called()
        self.ensure.reset_mock()
        with patch.object(apps, 'has', return_value=True):
            self.assertEqual(apps.module_action('verify', apps.catalog()['discord']['id']), 0)
            self.assertEqual(apps.module_action('install', apps.catalog()['slack']['id']), 0)
        self.ensure.assert_not_called()

    def test_custom_managed_desktop_is_preserved_before_submission(self):
        path = apps.gaming_desktop('slack'); path.parent.mkdir(parents=True)
        path.write_text('custom launcher\n')
        with patch.object(apps, 'has', return_value=True):
            with self.assertRaisesRegex(RuntimeError, 'was edited'):
                apps.ensure_gaming_shortcut('slack')
        self.assertEqual(path.read_text(), 'custom launcher\n')
        self.ensure.assert_not_called()

    def test_shortcut_failure_does_not_stop_independent_app_install(self):
        args = argparse.Namespace(apps_command='install', names=['discord', 'spotify'])
        with patch.object(apps, 'module_action', side_effect=[RuntimeError('Steam submission failed'), 0]) as action:
            self.assertEqual(apps.dispatch(args), 1)
            self.assertEqual(action.call_count, 2)

    def row(self, key='discord'):
        return dict(key='app:'+key, name=apps.catalog()[key]['name'], flatpak=apps.catalog()[key]['id'], kind='flatpak', owner=apps.catalog()[key]['module'], requires=[], visible=True)

    def test_existing_package_shortcut_retry_never_updates_or_reinstalls(self):
        with patch.object(apps, 'gaming_status', return_value='MISSING'), patch.object(apps, 'has', return_value=True), patch.object(setup_plan, 'command', return_value='commit'), patch.object(setup_install, '_flatpak') as install:
            self.assertIn('shortcut', setup_install.execute(self.row()))
            install.assert_not_called()
        self.ensure.return_value='PENDING_STEAM_REFRESH'
        with patch.object(apps, 'gaming_status', return_value='PENDING_STEAM_REFRESH'), patch.object(apps, 'has', return_value=True), patch.object(setup_plan, 'command', return_value='commit'), patch.object(setup_install, '_flatpak') as install:
            with self.assertRaisesRegex(setup_install.NeedsSetup, 'has not saved'):
                setup_install.execute(self.row())
            install.assert_not_called()

    def test_failed_package_install_never_submits(self):
        with patch.object(apps, 'gaming_status', return_value='MISSING'), patch.object(setup_plan, 'command', return_value=None), patch.object(setup_install, '_flatpak', side_effect=RuntimeError('download failed')):
            with self.assertRaisesRegex(RuntimeError, 'download failed'):
                setup_install.execute(self.row())
        self.ensure.assert_not_called()

    def test_read_only_preview_and_resume_verify_require_saved_shortcut(self):
        for state in ('MISSING', 'PENDING_STEAM_REFRESH', 'READY'):
            with self.subTest(state=state), patch.object(apps, 'gaming_status', return_value=state), patch.object(setup_plan, 'command', return_value='commit'):
                present, details=setup_plan.present(self.row())
                self.assertTrue(present)
                self.assertEqual(details['configuration'], state != 'READY')
                self.assertEqual(setup_install.verify(self.row()), state == 'READY')
        self.ensure.assert_not_called()
        self.assertFalse(apps.gaming_desktop('discord').exists())

    def test_resume_old_done_item_runs_missing_shortcut_instead_of_skipping(self):
        row=self.row(); plan={'modules':['utilities'], 'apps':['discord']}
        core.save_json(setup_install.state_path(), {'fingerprint':setup_plan.fingerprint(plan), 'items':{row['key']:{'status':'DONE'}}})
        with patch.object(setup_plan, 'items', return_value=(plan,[row])), patch.object(setup_plan, 'storage_budget', return_value=(self.home,None,'')), patch.object(setup_install, 'verify', side_effect=[False,True]), patch.object(setup_install, 'execute', return_value='Gaming Mode shortcut verified.') as execute:
            self.assertEqual(setup_install.run(resume=True), 0)
        execute.assert_called_once_with(row)
        self.assertEqual(json.loads(setup_install.state_path().read_text())['items'][row['key']]['status'], 'DONE')

    def test_chatgpt_uses_persistent_existing_browser_profile_and_only_requested_service(self):
        from deckctl import component_options, desktop
        with patch.object(component_options, 'effective', return_value={'chatgpt'}), patch.object(workspace, '_chrome', return_value=True), patch.object(desktop, 'apply') as icons:
            self.assertEqual(workspace.setup(only='chatgpt'), 0)
        icons.assert_called_once()
        self.ensure.assert_called_once_with('workspace:chatgpt', 'ChatGPT', workspace.APPS/'deck-workspace-chatgpt.desktop')
        runner=(workspace.BINDIR/'chatgpt').read_text()
        self.assertIn('--app="https://chatgpt.com/"', runner)
        self.assertNotIn('--user-data-dir',runner)
        self.assertFalse((workspace.APPS/'deck-workspace-claude.desktop').exists())

    def test_chatgpt_existing_launcher_flags_are_preserved(self):
        from deckctl import component_options, desktop
        workspace.APPS.mkdir(parents=True); workspace.BINDIR.mkdir(parents=True)
        path=workspace.APPS/'deck-workspace-chatgpt.desktop'
        runner=workspace.BINDIR/'chatgpt'
        path.write_text('existing desktop with custom flags\n')
        runner.write_text('existing runner with user profile\n')
        with patch.object(component_options, 'effective', return_value={'chatgpt'}), patch.object(workspace, '_chrome', return_value=True), patch.object(desktop, 'apply'):
            self.assertEqual(workspace.setup(only='chatgpt'),0)
        self.assertEqual(path.read_text(),'existing desktop with custom flags\n')
        self.assertEqual(runner.read_text(),'existing runner with user profile\n')
        self.ensure.assert_called_once_with('workspace:chatgpt','ChatGPT',path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
