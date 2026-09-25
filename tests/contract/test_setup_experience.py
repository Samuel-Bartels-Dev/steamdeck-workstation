#!/usr/bin/env python3
"""Portable choices, per-item dependency execution and honest preview contracts."""
import json
import os
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'lib'))
from deckctl import core, setup_plan, setup_install, setup_finish, setup_builder, setup_window, reliability, terminal, install_log


class Experience(unittest.TestCase):
    def test_ui_install_resume_retry_do_not_launch_konsole(self):
        from deckctl import setup_process
        session = setup_window.Session(); session.selected = ['base']
        process = Mock(); process.poll.return_value = 0
        with patch.object(setup_install,'running',return_value=False), patch.object(setup_plan,'items',return_value=(self.plan,[{'key':'app:slack'}])), patch.object(session,'progress',return_value={}), patch.object(setup_process,'start',return_value=process) as start, patch.object(setup_window.subprocess,'Popen') as terminal:
            for action in ('install','resume','retry'):
                session.start(action,'app:slack')
                command = start.call_args.args[0]
                self.assertEqual(command[1:3],['setup','install'])
                self.assertIn('--verbose',command)
                if action == 'resume': self.assertIn('--resume',command)
                if action == 'retry': self.assertIn('--item',command)
            terminal.assert_not_called()

    def test_terminal_launch_is_explicit_and_clears_noninteractive_mode(self):
        session = setup_window.Session(); session.selected = ['base']
        with patch.object(setup_install,'running',return_value=False), patch.object(setup_plan,'items',return_value=(self.plan,[{'key':'module:android'}])), patch.object(session,'progress',return_value={}), patch.object(setup_window.shutil,'which',return_value='/usr/bin/konsole'), patch.object(setup_window.subprocess,'Popen') as launch, patch.dict(os.environ,{'DECKCTL_UI_RUN':'1'}):
            session.start('interactive','module:android')
            self.assertEqual(launch.call_args.args[0][0],'/usr/bin/konsole')
            self.assertEqual(launch.call_args.args[0][-2:],['--item','module:android'])
            self.assertNotIn('DECKCTL_UI_RUN',launch.call_args.kwargs['env'])

    def test_ui_console_is_bounded_redacted_and_has_no_input(self):
        from deckctl import setup_process
        source = 'import sys; print("token=secret-value"); print("stdin="+repr(sys.stdin.read())); print("x"*100000); print("finished", file=sys.stderr); sys.exit(7)'
        process = setup_process.start([sys.executable,'-c',source],'test-plan')
        self.assertEqual(process.wait(5),7)
        result = setup_process.snapshot('test-plan')
        self.assertNotIn('secret-value',result['text'])
        self.assertIn('stdin=\'\'',result['text'])
        self.assertIn('finished',result['text'])
        self.assertEqual(result['exitCode'],7)
        self.assertLessEqual(len(result['text']),setup_process.LIMIT)
        self.assertEqual(setup_process.path().stat().st_mode & 0o777,0o600)
        self.assertEqual(setup_process.snapshot('different-plan'),{'text':''})
        unicode_run = setup_process.start([sys.executable,'-c',"for _ in range(30): print('🌸'*1000)"],'unicode-plan')
        self.assertEqual(unicode_run.wait(5),0)
        self.assertLessEqual(len(setup_process.snapshot('unicode-plan')['text'].encode('utf-8')),setup_process.LIMIT)

    def test_ui_defers_interactive_vendor_without_invoking_it(self):
        row = dict(key='module:android',kind='module',owner='android')
        with patch.dict(os.environ,{'DECKCTL_UI_RUN':'1'}), patch.object(setup_install,'verify',return_value=False), patch.object(setup_install,'_module') as vendor:
            with self.assertRaisesRegex(setup_install.NeedsSetup,'Continue in terminal'): setup_install.execute(row)
            vendor.assert_not_called()

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
            self.assertEqual((result['installedVersion'],result['availableVersion']),('old','new'))
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

    def test_new_saved_plan_does_not_inherit_old_process_success(self):
        session = setup_window.Session()
        session.operation = 'install'; session.process = Mock()
        session.process.poll.return_value = 0
        session.save(self.plan)
        result = session.progress()
        self.assertIsNone(result['operation'])
        self.assertIsNone(result['exitCode'])
        self.assertFalse(result['running'])

    def test_reopen_history_is_read_only_and_changed_plan_cannot_resume_old_results(self):
        rows = [dict(key=k,name=k,visible=True) for k in ('a','b')]
        core.save_json(setup_install.state_path(), {'fingerprint':setup_plan.fingerprint(self.plan),'startedAt':123,'items':{'a':{'status':'DONE','message':'Already up to date; verified.'},'b':{'status':'RUNNING'}}})
        before = setup_install.state_path().read_bytes()
        with patch.object(setup_plan,'items',return_value=(self.plan,rows)), patch.object(setup_install,'verify',side_effect=AssertionError('startup must not install or verify providers')):
            result = setup_window.Session().progress()
        self.assertTrue(result['hasHistory']); self.assertTrue(result['resumable'])
        self.assertEqual(result['unfinished'],1)
        self.assertEqual(result['items'][0]['status'],'INTERRUPTED')
        self.assertEqual(result['items'][1]['resultLabel'],'Already current')
        self.assertEqual(before,setup_install.state_path().read_bytes())
        with patch.object(setup_plan,'items',return_value=({**self.plan,'palette':'bubblegum'},rows)):
            changed = setup_window.Session().progress()
        self.assertTrue(changed['historyPlanChanged']); self.assertFalse(changed['resumable'])
        self.assertFalse(changed['hasHistory'])

    def test_results_only_claim_update_when_reported_and_include_next_steps(self):
        rows = [dict(key=k,name=k,visible=True,followup='signin') for k in ('updated','generic','failed')]
        records = {'updated':{'status':'DONE','message':'Updated and verified.'}, 'generic':{'status':'DONE','message':'Installation verified.'}, 'failed':{'status':'FAILED'}}
        core.save_json(setup_install.state_path(),{'fingerprint':setup_plan.fingerprint(self.plan),'items':records})
        with patch.object(setup_plan,'items',return_value=(self.plan,rows)):
            results = {r['key']:r for r in setup_window.Session().progress()['items']}
        self.assertEqual(results['updated']['resultLabel'],'Updated')
        self.assertEqual(results['generic']['resultLabel'],'Verified')
        self.assertIn('sign-in',results['updated']['nextAction'])
        self.assertIn('retry',results['failed']['nextAction'])

    def test_review_notes_explain_privileges_restart_and_signin(self):
        notes = setup_plan.review_notes(dict(key='module:decky',kind='module'))
        self.assertIn('sudo',' '.join(notes)); self.assertIn('restart Decky',' '.join(notes))
        notes = setup_plan.review_notes(dict(key='app:slack',kind='flatpak',flatpak='com.slack.Slack',followup='signin'))
        self.assertIn('user account',' '.join(notes)); self.assertIn('sign in',' '.join(notes))

    def test_successful_retry_does_not_hide_other_unfinished_items(self):
        rows = [dict(key=k, name=k, visible=True) for k in ('done', 'failed', 'waiting')]
        records = {'done': {'status': 'DONE'}, 'failed': {'status': 'FAILED'}}
        core.save_json(setup_install.state_path(), {'fingerprint': setup_plan.fingerprint(self.plan), 'items': records})
        session = setup_window.Session(); session.operation = 'install'
        session.process = Mock(); session.process.poll.return_value = 0
        with patch.object(setup_plan, 'items', return_value=(self.plan, rows)):
            result = session.progress()
            self.assertEqual(result['exitCode'], 2)
            self.assertEqual(result['summary'], {'total': 3, 'done': 1, 'attention': 1})
            self.assertEqual([r['key'] for r in result['items']], ['failed', 'waiting', 'done'])
            session.operation = 'accounts'
            self.assertEqual(session.progress()['exitCode'], 0)
            session.operation = 'install'
            core.save_json(setup_install.state_path(), {'fingerprint': setup_plan.fingerprint(self.plan), 'items': {k: {'status': 'DONE'} for k in ('done', 'failed', 'waiting')}})
            self.assertEqual(session.progress()['exitCode'], 0)

    def test_failure_log_captures_child_stderr_and_traceback_privately(self):
        with self.assertRaisesRegex(RuntimeError, 'installer failed'):
            with install_log.capture('module:base') as path:
                subprocess.run([sys.executable, '-c', 'import sys; print("provider error: access_token=example-secret", file=sys.stderr)'], check=True)
                raise RuntimeError('installer failed')
        text = path.read_text()
        self.assertIn('provider error:', text)
        self.assertIn('RuntimeError: installer failed', text)
        self.assertNotIn('example-secret', text)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertLessEqual(path.stat().st_size, install_log.LIMIT)
        with install_log.capture('module:base') as same:
            os.write(2, b'new attempt\n')
        self.assertEqual(path, same)
        self.assertNotIn('installer failed', same.read_text())

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

    def test_resume_after_interrupt_and_extraction_failure_preserves_healthy_work(self):
        rows = [dict(key=k, name=k, kind='component', requires=[]) for k in ('healthy','broken')]
        personal = self.root/'personal-config'; personal.write_text('keep me')
        calls = []
        def interrupted(row):
            calls.append(row['key'])
            if row['key'] == 'broken': raise KeyboardInterrupt()
        with patch.object(setup_plan,'items',return_value=(self.plan,rows)), patch.object(setup_plan,'storage_budget',return_value=(self.root,None,'')), patch.object(setup_install,'verify',return_value=True):
            with patch.object(setup_install,'execute',side_effect=interrupted):
                self.assertEqual(setup_install.run(),2)
            self.assertEqual(setup_install.snapshot()['items']['broken']['status'],'INTERRUPTED')
            for failure in (RuntimeError('Interrupted extraction'), OSError('Network disconnected')):
                with patch.object(setup_install,'execute',side_effect=failure) as execute:
                    self.assertEqual(setup_install.run(resume=True),1)
                    self.assertEqual([c.args[0]['key'] for c in execute.call_args_list],['broken'])
            with patch.object(setup_install,'execute') as execute:
                self.assertEqual(setup_install.run(resume=True),0)
                self.assertEqual([c.args[0]['key'] for c in execute.call_args_list],['broken'])
        self.assertEqual(personal.read_text(),'keep me')

    def test_quiet_provider_reports_activity_without_inventing_failure(self):
        rows = [dict(key='a',name='A',visible=True)]
        core.save_json(setup_install.state_path(), {'fingerprint':setup_plan.fingerprint(self.plan), 'items':{'a':{'status':'RUNNING','startedAt':100,'updatedAt':110}}})
        with patch.object(setup_plan,'items',return_value=(self.plan,rows)), patch.object(setup_install,'running',return_value=True), patch.object(setup_window.time,'time',return_value=210):
            item = setup_window.Session().progress()['items'][0]
        self.assertEqual(item['quietSeconds'],100)
        self.assertEqual(item['status'],'RUNNING')
        self.assertIn('quiet operation',item['activityNotice'])

    def test_bounded_log_keeps_latest_output_and_redacts_it(self):
        with patch.object(install_log,'LIMIT',256), install_log.capture('bounded'):
            for i in range(40): install_log.note('provider output line '+str(i))
            install_log.note('LATEST token=private-value')
        content = install_log.read('bounded')
        self.assertIn('LATEST token=<redacted>',content)
        self.assertNotIn('private-value',content)
        self.assertLessEqual(install_log.path_for('bounded').stat().st_size,256)

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
