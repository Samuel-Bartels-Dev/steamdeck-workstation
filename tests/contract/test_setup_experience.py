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
    def test_explicit_interactive_output_never_enters_raw_archives(self):
        from deckctl import production_cli, run_log
        row = dict(key='remote:tailscale', kind='component', owner='remote', component='tailscale',
                   name='Tailscale', requires=[], visible=True)
        private = 'https://login.tailscale.com/a/SYNTHETIC-PRIVATE peer-private-host'
        def vendor(_):
            print(private)
            os.write(2, (private+'\n').encode())
        with patch.dict(os.environ, {}, clear=True), patch.object(setup_plan,'items',return_value=(self.plan,[row])), patch.object(setup_install,'execute',side_effect=vendor), patch.object(setup_install,'verify',return_value=True), patch.object(setup_plan,'storage_budget',return_value=(self.root,None,'')):
            self.assertEqual(production_cli.operation('install', lambda: setup_install.run()), 0)
        for log in run_log.root().rglob('*'):
            if log.is_file(): self.assertNotIn('SYNTHETIC-PRIVATE', log.read_text())
        self.assertFalse(install_log.path_for(row['key']).exists())

    def test_failed_preflight_is_durable_and_console_identifies_current_run(self):
        from deckctl import production_cli, run_log, setup_process
        old_id = 'install-20250101T010101-aaaaaaaaaaaa'
        fingerprint = setup_plan.fingerprint(self.plan)
        core.save_json(setup_install.state_path(), {'fingerprint':fingerprint,'run_id':old_id,'startedAt':1})
        report = {'status':'FAIL','checks':[{'status':'FAIL','name':'storage','message':'Insufficient space'}]}
        with patch.dict(os.environ, {'DECKCTL_UI_RUN':'1'}), patch.object(production_cli.preflight,'report',return_value=report):
            self.assertEqual(production_cli.operation('install', Mock(side_effect=AssertionError('Must not install')), check=True), 1)
        latest = run_log.runs()[0]
        archive = Path(latest['directory'])/install_log.path_for('run:'+latest['run_id']).name
        self.assertIn('FAIL storage: Insufficient space', archive.read_text())
        handle = setup_process.start([sys.executable,'-c','print('+repr('Run: '+latest['run_id'])+'); print("FAIL storage: Insufficient space"); raise SystemExit(1)'], fingerprint)
        self.assertEqual(handle.wait(5), 1)
        with patch.object(setup_plan,'items',return_value=(self.plan,[])):
            console = setup_window.Session().console()
        self.assertEqual(console['runId'], latest['run_id'])
        self.assertNotIn(old_id, console['logDirectory'])
        self.assertEqual(console['logFile'], str(archive))

    def test_stdout_stderr_split_secrets_and_unicode_are_archived_per_run(self):
        from deckctl import run_log
        with run_log.execution('install') as journal:
            with install_log.capture('terminal:sample'):
                source = ('import os,time; os.write(1,b"[terminal:sample] Downloading\\naccess_tok"); '
                          'time.sleep(.05); os.write(1,b"en=split-private\\n"); '
                          'os.write(2,"\\x1b[31mERROR: café 🌸\\x1b[0m\\n".encode())')
                subprocess.run([sys.executable, '-c', source], check=True)
            run_log.archive_item('terminal:sample')
            journal.finish(1)
        text = (journal.path/install_log.path_for('terminal:sample').name).read_text()
        self.assertIn('[terminal:sample] Downloading', text)
        self.assertIn('ERROR: café 🌸', text)
        self.assertNotIn('split-private', text)
        self.assertNotIn('\x1b', text)
        # A later attempt overwrites the recent item view, never its historical run.
        with install_log.capture('terminal:sample'): print('new attempt')
        self.assertEqual((journal.path/install_log.path_for('terminal:sample').name).read_text(), text)

    def test_owned_shutdown_stops_ignoring_child_and_grandchild(self):
        from deckctl import setup_process
        import time
        pidfile = self.root/'grandchild.pid'
        source = ('import os,signal,time,pathlib; signal.signal(signal.SIGINT,signal.SIG_IGN); '
                  'child=os.fork(); pathlib.Path('+repr(str(pidfile))+').write_text(str(os.getpid())) if child==0 else None; '
                  'time.sleep(30)')
        handle = setup_process.start([sys.executable, '-c', source], 'shutdown')
        try:
            deadline = time.monotonic()+3
            while not pidfile.exists() and time.monotonic()<deadline: time.sleep(.01)
            self.assertTrue(pidfile.exists())
            started = time.monotonic(); handle.close(grace=.1)
            self.assertLess(time.monotonic()-started, 3)
            self.assertEqual(handle.wait(3), -9)
            child = Path('/proc')/pidfile.read_text()
            if (child/'stat').exists(): self.assertEqual((child/'stat').read_text().split()[2], 'Z')
            self.assertEqual(list(core.STATE.glob('setup-control-*')), [])
        finally: handle.close(grace=.1)

    def test_local_link_is_distinct_from_internet_and_rate(self):
        from deckctl import setup_activity
        link = self.root/'net/wlan0'; (link/'device').mkdir(parents=True)
        (link/'carrier').write_text('0\n')
        self.assertEqual(setup_activity.network_status(link.parent)['status'], 'OFFLINE')
        (link/'carrier').write_text('1\n')
        result = setup_activity.network_status(link.parent)
        self.assertEqual(result['status'], 'LINK_UP')
        self.assertIn('Internet access not checked', result['message'])
        (link/'carrier').unlink()
        self.assertEqual(setup_activity.network_status(link.parent)['status'], 'UNKNOWN')

    def test_active_space_reports_unknown_and_original_allowance(self):
        from deckctl import setup_activity
        self.assertEqual(setup_activity.storage_status({'key':'legacy'})['status'], 'UNKNOWN')
        with patch.object(setup_plan, 'storage_budget', return_value=(self.root, 200, 'Original allowance')), patch.object(setup_activity.shutil, 'disk_usage', return_value=Mock(free=100)):
            result = setup_activity.storage_status({'key':'test'})
        self.assertEqual(result['status'], 'INSUFFICIENT')
        self.assertEqual(result['allowanceBytes'], 200)
        self.assertEqual(result['freeBytes'], 100)

    def test_docker_action_is_selected_captured_runner_and_accounts_rejected(self):
        from deckctl import setup_process
        session = setup_window.Session(); session.selected = ['base']
        handle = Mock(); handle.poll.return_value = 0
        with patch.object(setup_install, 'running', return_value=False), patch.object(setup_plan, 'items', return_value=(self.plan,[{'key':'dev:docker'}])), patch.object(session, 'progress', return_value={}), patch.object(setup_process, 'start', return_value=handle) as start:
            session.start('docker')
            self.assertEqual(start.call_args.args[0][1:], ['setup','install','--item','dev:docker','--verbose'])
            with self.assertRaises(ValueError): session.start('accounts')

    def test_queue_pause_waits_at_boundary_and_continue_releases_it(self):
        import threading
        import time
        control = core.STATE/'setup-control-test.json'
        core.save_json(control,{'pause':True})
        state = {}
        with patch.dict(os.environ,{'DECKCTL_UI_RUN':'1','DECKCTL_UI_CONTROL':str(control)}):
            thread = threading.Thread(target=setup_install.queue_checkpoint,args=(state,))
            thread.start()
            try:
                deadline = time.monotonic()+2
                while state.get('queueStatus') != 'PAUSED' and time.monotonic()<deadline: time.sleep(.01)
                self.assertEqual(state.get('queueStatus'),'PAUSED')
                self.assertTrue(thread.is_alive())
            finally:
                core.save_json(control,{'pause':False}); thread.join(2)
            self.assertFalse(thread.is_alive()); self.assertEqual(state['queueStatus'],'RUNNING')
            core.save_json(control,{'cancel':True})
            with self.assertRaises(KeyboardInterrupt): setup_install.queue_checkpoint(state)

    def test_owned_run_controls_cancel_and_cleanup(self):
        from deckctl import setup_process
        process = setup_process.start([sys.executable,'-c','import time; time.sleep(30)'],'controls')
        try:
            self.assertTrue(process.control('pause')['pause'])
            self.assertFalse(process.control('continue')['pause'])
            self.assertTrue(process.control('cancel')['cancel'])
            self.assertNotEqual(process.wait(5),0)
            self.assertFalse(process.controls()['available'])
            with self.assertRaises(ValueError): process.control('pause')
            self.assertEqual(list(core.STATE.glob('setup-control-*')),[])
        finally:
            if process.poll() is None: process.control('cancel'); process.wait(5)

    def test_force_stop_requires_cancel_and_grace_period(self):
        from deckctl import setup_process
        import time
        ready = core.STATE/'force-ready'
        command = [sys.executable, '-c',
                   'import signal,time,pathlib; signal.signal(signal.SIGINT, signal.SIG_IGN); '
                   'pathlib.Path('+repr(str(ready))+').touch(); time.sleep(30)']
        process = setup_process.start(command, 'force-test')
        try:
            deadline = time.monotonic()+3
            while not ready.exists() and time.monotonic()<deadline: time.sleep(.01)
            self.assertTrue(ready.exists())
            with self.assertRaises(ValueError): process.control('force')
            process.control('cancel')
            with self.assertRaises(ValueError): process.control('force')
            time.sleep(10.1)
            self.assertTrue(process.controls()['forceAvailable'])
            process.control('force')
            self.assertEqual(process.wait(5), -9)
            self.assertFalse(process.controls()['available'])
        finally:
            if process.poll() is None:
                time.sleep(10.1)
                if not process.controls()['cancel']: process.control('cancel'); time.sleep(10.1)
                process.control('force'); process.wait(5)

    def test_activity_rates_resets_missing_devices_and_bounded_history(self):
        from deckctl import setup_activity
        sampler = setup_activity.Sampler()
        snapshots = [dict(network={'wifi':(100,)},disk={'disk':(100,200)}),dict(network={'wifi':(300,)},disk={'disk':(500,800)}),dict(network={'wifi':(1,)},disk={})]
        with patch.object(setup_activity,'counters',side_effect=snapshots), patch.object(setup_activity.time,'monotonic',side_effect=[0,2,4]):
            self.assertIsNone(sampler.sample()[-1]['network'])
            result = sampler.sample()[-1]
            self.assertEqual((result['network'],result['read'],result['write']),(100,200,300))
            result = sampler.sample()[-1]
            self.assertIsNone(result['network']); self.assertIsNone(result['read'])
        with patch.object(setup_activity,'counters',return_value={'network':{},'disk':{}}), patch.object(setup_activity.time,'monotonic',side_effect=range(6,150,2)):
            for _ in range(65): sampler.sample()
        self.assertEqual(len(sampler.history),60)

    def test_activity_excludes_virtual_disks_and_uses_sector_bytes(self):
        from deckctl import setup_activity
        physical = self.root/'block/nvme0n1'; (physical/'device').mkdir(parents=True)
        (physical/'stat').write_text('1 0 10 0 1 0 20 0 0 0 0')
        virtual = self.root/'block/dm-0'; virtual.mkdir(); (virtual/'stat').write_text('1 0 999 0 1 0 999 0 0 0 0')
        self.assertEqual(setup_activity.counters(self.root)['disk'],{'nvme0n1':(5120,10240)})

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

    def test_sudo_session_uses_native_askpass_and_invalidates_on_exit(self):
        from deckctl import privilege, preflight
        calls = []
        def run(args, **kwargs):
            calls.append((args, kwargs))
            return subprocess.CompletedProcess(args, 0)
        with patch.dict(os.environ, {'DECKCTL_UI_RUN':'1','DISPLAY':':0'}), patch.object(privilege.shutil,'which',return_value='/usr/bin/sudo'), patch.object(privilege.Path,'is_file',return_value=True), patch.object(preflight,'sudo_readiness',return_value={'state':'PASSWORD_SET'}), patch.object(privilege.subprocess,'run',side_effect=run):
            with privilege.Session() as permission:
                permission.prepare()
                self.assertEqual(privilege.command(['systemctl','restart','plugin_loader']), ['sudo','-A','systemctl','restart','plugin_loader'])
            with self.assertRaises(RuntimeError): privilege.command(['true'])
        self.assertEqual([call[0] for call in calls], [['sudo','-k'],['sudo','-A','-v'],['sudo','-k']])
        self.assertEqual(calls[1][1]['env']['SUDO_ASKPASS'], str(privilege.HELPER))
        self.assertEqual(calls[1][1]['stdout'], subprocess.DEVNULL)
        self.assertNotIn('input', calls[1][1])
        self.assertFalse(core.STATE.exists())

    def test_sudo_failure_and_interrupt_invalidate_ticket(self):
        from deckctl import privilege, preflight
        for failure in (subprocess.CompletedProcess([],1), KeyboardInterrupt()):
            with self.subTest(failure=type(failure).__name__), patch.dict(os.environ, {'DECKCTL_UI_RUN':'1','DISPLAY':':0'}), patch.object(privilege.shutil,'which',return_value='/usr/bin/sudo'), patch.object(privilege.Path,'is_file',return_value=True), patch.object(preflight,'sudo_readiness',return_value={'state':'PASSWORD_SET'}), patch.object(privilege.subprocess,'run',side_effect=[subprocess.CompletedProcess([],0),failure,subprocess.CompletedProcess([],0)]) as run:
                with self.assertRaises((RuntimeError,KeyboardInterrupt)), privilege.Session() as permission:
                    permission.prepare()
                self.assertEqual(run.call_args.args[0], ['sudo','-k'])
                with self.assertRaises(RuntimeError): privilege.command(['true'])

    def test_fresh_deck_reports_missing_password_before_sudo(self):
        from deckctl import privilege, preflight
        with patch.dict(os.environ, {'DISPLAY':':0'}), patch.object(privilege.shutil,'which',return_value='/usr/bin/sudo'), patch.object(privilege.Path,'is_file',return_value=True), patch.object(preflight,'sudo_readiness',return_value={'state':'PASSWORD_MISSING','message':'Run passwd first'}), patch.object(privilege.subprocess,'run') as run:
            with privilege.Session() as permission, self.assertRaisesRegex(RuntimeError, 'passwd'):
                permission.prepare()
            run.assert_not_called()

    def test_admin_cancel_precedes_install_and_does_not_block_user_apps(self):
        from deckctl import privilege
        rows = [dict(key='app:test',name='User app',kind='flatpak',requires=[]),
                dict(key='dependency:css-profile',name='Colors',kind='css-profile',requires=[])]
        order = []
        def prepare():
            order.append('authorize')
            raise RuntimeError('Authorization cancelled; retry to open the password dialog.')
        with patch.dict(os.environ,{'DECKCTL_UI_RUN':'1'}), patch.object(setup_plan,'items',return_value=(self.plan,rows)), patch.object(setup_plan,'storage_budget',return_value=(self.root,None,'')), patch.object(setup_install,'verify',side_effect=lambda row: row['kind']=='flatpak'), patch.object(privilege.Session,'prepare',side_effect=prepare), patch.object(setup_install,'execute',side_effect=lambda row: order.append(row['key'])):
            self.assertEqual(setup_install.run(),2)
        self.assertEqual(order,['authorize','app:test'])
        records = setup_install.snapshot()['items']
        self.assertEqual(records['app:test']['status'],'DONE')
        self.assertEqual(records['dependency:css-profile']['status'],'NEEDS_SETUP')
        self.assertIn('password dialog',records['dependency:css-profile']['message'])

    def test_css_runs_inline_after_authorization_and_healthy_items_do_not_prompt(self):
        from deckctl import privilege, css_stack
        row = dict(key='dependency:css-profile', name='Colors', kind='css-profile', requires=[])
        self.assertFalse(setup_install.interactive_provider(row))
        with patch.dict(os.environ,{'DECKCTL_UI_RUN':'1'}), patch.object(setup_install,'verify',return_value=False), patch.object(css_stack,'apply',return_value=0) as apply:
            with self.assertRaises(RuntimeError): setup_install.execute(row)
            apply.assert_not_called()
            token = privilege._authorized.set(True)
            try: setup_install.execute(row)
            finally: privilege._authorized.reset(token)
            apply.assert_called_once()
        with patch.dict(os.environ,{'DECKCTL_UI_RUN':'1'}), patch.object(setup_plan,'items',return_value=(self.plan,[row])), patch.object(setup_plan,'storage_budget',return_value=(self.root,None,'')), patch.object(setup_install,'verify',return_value=True), patch.object(privilege.Session,'prepare') as prepare:
            self.assertEqual(setup_install.run(),0)
            prepare.assert_not_called()

    def test_keeper_existing_extension_is_reused_and_login_remains_separate(self):
        row = dict(key='media:keeper', name='KeeperFill', kind='component', owner='media',
                   component='keeper', requires=[], visible=True, followup='signin')
        with patch.object(core, '_keeper_installed', return_value=True), patch.object(setup_install, '_run') as install, patch.object(core, 'media_keeper_setup') as setup:
            self.assertEqual(setup_install.execute(row), 'Existing installation verified.')
            self.assertTrue(setup_install.verify(row))
            install.assert_not_called(); setup.assert_not_called()
            with patch.object(setup_plan, 'items', return_value=(self.plan,[row])):
                result = setup_finish.rows()[0]
                self.assertTrue(result['installed'])
                self.assertEqual(result['status'], 'Needs sign-in')
                self.assertTrue(result['canConfirm'])
        with patch.object(core, '_keeper_installed', return_value=False):
            with self.assertRaisesRegex(setup_install.NeedsSetup, 'Install KeeperFill in Chrome'):
                setup_install.execute(row)
            self.assertFalse(setup_install.verify(row))

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
