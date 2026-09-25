#!/usr/bin/env python3
"""Isolated failure/retention/diagnostic regression contracts; no provisioning."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'lib'))
from deckctl import core, run_log, compatibility, diagnostics, cli, preflight


class Production(unittest.TestCase):
    def test_lean_runtime_install_repeat_verify_and_corruption(self):
        import subprocess
        from deckctl import runtime_package
        home = Path(self.temp.name)/'runtime-home'; home.mkdir()
        env = dict(os.environ, HOME=str(home))
        installer = ROOT/'tools/install-control-plane'
        for _ in range(2):
            result = subprocess.run([str(installer), str(ROOT)], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        installed = home/'.local/share/steamdeck-workstation/current'
        for name in ('tests', '.github', 'tasks', 'AGENTS.md', 'tools/build-release', 'docs/ai'):
            self.assertFalse((installed/name).exists(), name)
        self.assertTrue((installed/'lib/deckctl/ui/Setup.qml').is_file())
        self.assertTrue((installed/'host').is_dir())
        result = subprocess.run([str(installed/'bin/deckctl'), 'repo', 'validate'], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('RUNTIME INTEGRITY PASS', result.stdout)
        self.assertNotIn('REPO VALIDATION PASS', result.stdout)
        result = subprocess.run([str(installed/'tools/install-control-plane'), str(installed)], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for args in (['setup','customize','--help'], ['health','--help'], ['update','--help']):
            result = subprocess.run([str(installed/'bin/deckctl'), *args], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([str(installed/'bin/deckctl'), 'ai', 'task', 'base', 'example'], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('source checkout', result.stderr)
        self.assertFalse((installed/'tasks').exists())
        target = installed/'lib/deckctl/ui/Setup.qml'
        original = target.read_bytes(); target.write_bytes(b'broken')
        with self.assertRaisesRegex(ValueError, 'integrity mismatch'): runtime_package.validate(installed)
        result = subprocess.run([str(installed/'tools/install-control-plane'), str(installed)], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        target.write_bytes(original)
        extra = installed/'unexpected.txt'; extra.write_text('not runtime')
        with self.assertRaisesRegex(ValueError, 'non-runtime'): runtime_package.validate(installed)
        extra.unlink()
        target.unlink(); target.symlink_to(ROOT/'lib/deckctl/ui/Setup.qml')
        with self.assertRaisesRegex(ValueError, 'symlink'): runtime_package.validate(installed)

    def test_css_inventory_detects_display_name_without_claiming_palette_ready(self):
        from deckctl import css_stack, setup_plan, setup_inventory, setup_install
        themes = Path(self.temp.name)/'themes'
        theme = themes/'CapyMenu (QAM)'; theme.mkdir(parents=True)
        (theme/'theme.json').write_text(json.dumps({'name':'CapyMenu (QAM)', 'display_name':'Chromahon (QAM)', 'version':'v3.0.1'}))
        row = {'key':'css:Chromahon (QAM)', 'kind':'css', 'component':'Chromahon (QAM)', 'name':'Chromahon (QAM)'}
        with patch.object(css_stack,'THEMES_DIR',themes), patch.object(css_stack,'component_ready',return_value=False):
            installed, evidence = setup_plan.present(row)
            self.assertTrue(installed); self.assertFalse(evidence['configured'])
            local = setup_inventory.local(row)
            self.assertEqual(local['label'], 'Installed · needs setup')
            self.assertEqual(setup_plan.inspect(row,online=False)['action'], 'CONFIGURE')
            self.assertEqual(setup_inventory.remote(row,local)['status'], 'NEEDS_SETUP')
            self.assertFalse(setup_install.verify(row))
            (theme/'theme.json').write_text('invalid')
            self.assertFalse(setup_plan.present(row)[0])
            self.assertEqual(setup_inventory.local(row)['status'], 'MISSING')

    def test_password_readiness_never_prompts_or_confuses_locked_with_set(self):
        import pwd
        import subprocess
        user = pwd.getpwuid(os.getuid()).pw_name
        for value, expected in [('P','PASSWORD_SET'),('NP','PASSWORD_MISSING'),('L','PASSWORD_LOCKED'),('unexpected','UNKNOWN')]:
            with patch.object(preflight.shutil,'which',return_value='/usr/bin/sudo'), patch.object(preflight.subprocess,'run',return_value=subprocess.CompletedProcess([],0,user+' '+value,'password-like sensitive stderr')) as run:
                result = preflight.sudo_readiness()
                self.assertEqual(result['state'],expected)
                self.assertEqual(result['status'],'PASS' if value == 'P' else 'WARN')
                self.assertNotIn('sensitive',str(result))
                run.assert_called_once()
                self.assertEqual(run.call_args.args[0],['passwd','--status',user])
                self.assertEqual(run.call_args.kwargs['timeout'],5)
        with patch.object(preflight.shutil,'which',return_value=None), patch.object(preflight.subprocess,'run') as run:
            self.assertEqual(preflight.sudo_readiness()['state'],'UNAVAILABLE'); run.assert_not_called()
        with patch.object(preflight.shutil,'which',return_value='/usr/bin/sudo'), patch.object(preflight.subprocess,'run',side_effect=subprocess.TimeoutExpired('passwd',5)):
            self.assertEqual(preflight.sudo_readiness()['state'],'UNKNOWN')

    def test_setup_exposes_fresh_install_password_guidance(self):
        from deckctl import setup_window
        warning = dict(status='WARN',state='PASSWORD_MISSING',message='Run passwd in Konsole')
        with patch.object(preflight,'sudo_readiness',return_value=warning):
            self.assertEqual(setup_window.Session().snapshot()['sudoReadiness'],warning)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)/'state'
        self.patcher = patch.object(core, 'STATE', self.state)
        self.patcher.start(); self.addCleanup(self.patcher.stop)
        config_patch = patch.object(core, 'CONFIG_HOME', Path(self.temp.name)/'config')
        config_patch.start(); self.addCleanup(config_patch.stop)

    def test_distinct_runs_plan_timing_and_private_files(self):
        for _ in range(2):
            with run_log.execution('install') as run:
                run.event('test', 'ERROR', 'FAILED', 'access_token=secret-example password="quoted secret"')
                run.finish(1)
        rows = run_log.runs()
        self.assertEqual(len(rows), 2)
        for row in rows:
            path = Path(row['directory'])
            self.assertGreaterEqual(row['duration_ms'], 0)
            self.assertEqual(path.stat().st_mode & 0o777, 0o700)
            self.assertNotIn('secret-example', (path/'events.jsonl').read_text())
            for line in (path/'events.jsonl').read_text().splitlines(): json.loads(line)

    def test_cleanup_keeps_active_and_newest_failure(self):
        with run_log.execution('install') as active:
            with run_log.execution('install') as nested:
                self.assertIs(active, nested)
            # Independent run simulates another process, protected by its flock.
            failed = run_log.Run('repair'); failed.finish(1); failed.lock.close()
            run_log.clean(all_runs=True)
            self.assertTrue(active.path.exists())
            self.assertTrue(failed.path.exists())
            active.finish(0)
        run_log.clean(all_runs=True)
        self.assertFalse(active.path.exists())
        self.assertTrue(failed.path.exists())

    def test_retention_and_unknown_files(self):
        for _ in range(13):
            with run_log.execution('install') as run: run.finish(0)
        self.assertEqual(len(run_log.runs()), 10)
        path = Path(run_log.runs()[-1]['directory'])
        (path/'personal.txt').write_text('keep')
        run_log.clean(all_runs=True)
        self.assertTrue((path/'personal.txt').exists())

    def test_symlink_logs_refused(self):
        self.state.mkdir()
        (self.state/'logs').symlink_to(Path(self.temp.name), target_is_directory=True)
        with self.assertRaises(ValueError): run_log.Run('install')

    def test_exception_records_failed_run(self):
        with self.assertRaises(RuntimeError):
            with run_log.execution('repair'): raise RuntimeError('injected interruption')
        self.assertEqual(run_log.runs()[0]['status'], 'FAIL')

    def test_unknown_future_os_never_inherits_tested(self):
        host = dict(os='steamos', version='3.8', build='one', architecture='x86_64', model='oled', kernel='kernel')
        record = dict(host, component='workstation', component_version='1', status='TESTED')
        self.assertEqual(compatibility.resolve('workstation', '1', host, [record])['status'], 'TESTED')
        self.assertEqual(compatibility.resolve('workstation', '1', dict(host, version='99'), [record])['status'], 'UNKNOWN')
        self.assertEqual(compatibility.resolve('workstation', '2', host, [record])['status'], 'UNKNOWN')

    def test_doctor_never_calls_repair(self):
        with patch.object(core, 'module_status', return_value={'status':'FAILED','message':'missing loader'}), patch.object(core, 'doctor', side_effect=AssertionError('mutated')), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(diagnostics.diagnose('decky', True), 1)

    def test_stopped_docker_not_success(self):
        with patch('deckctl.containers.status_data', return_value={'status':'STOPPED_OR_UNREACHABLE'}), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(diagnostics.diagnose('docker', True), 1)

    def test_health_exit_propagates_failed_modules(self):
        with patch('deckctl.lifecycle.health', return_value={'modules':{'decky':{'status':'FAILED'}}}):
            self.assertEqual(cli.main(['health', '--json']), 1)

    def test_space_reserve_and_readonly(self):
        with patch.object(core, 'settings', return_value={'storage_reserve_bytes':0}):
            with self.assertRaises(ValueError): preflight.reserve()
        with patch('os.access', return_value=False):
            self.assertEqual(preflight.destination(Path(self.temp.name))['status'], 'FAIL')

    def test_download_failure_preserves_previous_and_cleans_stage(self):
        from deckctl import downloads
        destination = Path(self.temp.name)/'installer'
        destination.write_text('known good')
        response = io.BytesIO(b'<html>error</html>')
        response.headers = {'Content-Length':str(len(response.getvalue()))}
        response.geturl = lambda: 'https://example.invalid/installer'
        with patch('urllib.request.urlopen', return_value=response):
            with self.assertRaises(ValueError):
                downloads.fetch('https://example.invalid/installer', destination, validate=downloads.desktop_entry)
        self.assertEqual(destination.read_text(), 'known good')
        self.assertFalse(list(destination.parent.glob('.download-*')))

    def test_checksum_and_partial_download_rejected(self):
        from deckctl import downloads
        destination = Path(self.temp.name)/'installer'
        for length, digest in [('99', None), ('3', '0'*64), ('0', None)]:
            response = io.BytesIO(b'abc'); response.headers = {'Content-Length':length}
            response.geturl = lambda: 'https://example.invalid/file'
            with patch('urllib.request.urlopen', return_value=response):
                with self.assertRaises(ValueError): downloads.fetch('https://example.invalid/file', destination, sha256=digest)
            self.assertFalse(destination.exists())

    def test_wrong_card_uuid_and_duplicate_labels(self):
        devices = [{'label':'DECK-EMU','uuid':'wrong','mountpoints':[self.temp.name]}]
        with patch.object(core, 'storage_devices', return_value=devices), patch.object(core, 'settings', return_value={'storage_devices':{'emulation':{'uuid':'intended'}}}):
            row = preflight.storage_report()[-1]
            self.assertEqual(row['status'], 'FAIL')
            self.assertIn('UUID', row['message'])
        with patch.object(core, 'storage_devices', return_value=devices*2), patch.object(core, 'settings', return_value={}):
            self.assertEqual(preflight.storage_report()[-1]['status'], 'FAIL')

    def test_stable_gate_rejects_missing_failed_or_stale_evidence(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('release_gate', ROOT/'tools/release-gate.py')
        gate = importlib.util.module_from_spec(spec); spec.loader.exec_module(gate)
        report = dict(schema_version=1, version='1.2.3', candidate='1.2.3-rc1', source_sha256='abc',
                      date='2026-09-24', tester='test fixture', hardware='oled', steamos='test', kernel='test', decky='test',
                      gates={key:{'status':'PASS','evidence':'fixture only'} for key in gate.GATES})
        gate.validate(report, '1.2.3', 'abc')
        with self.assertRaises(ValueError): gate.validate(report, '1.2.3', 'changed')
        report['gates']['gaming_mode']['status'] = 'NOT_TESTED'
        with self.assertRaises(ValueError): gate.validate(report, '1.2.3', 'abc')

    def test_atomic_theme_failure_preserves_existing(self):
        from deckctl import appearance
        source = Path(self.temp.name)/'source'; source.write_text('new theme')
        target = Path(self.temp.name)/'target'; target.write_text('old theme')
        with patch.object(appearance, 'render', side_effect=lambda value:value), patch('os.replace', side_effect=OSError('injected full filesystem')):
            with self.assertRaises(OSError): appearance.write(source, target)
        self.assertEqual(target.read_text(), 'old theme')
        self.assertFalse(list(target.parent.glob('.deckctl-theme-*')))

    def test_candidate_control_plane_and_public_resolution(self):
        import shutil
        import subprocess
        source = Path(self.temp.name)/'candidate'
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns('.git','__pycache__','release'))
        (source/'VERSION').write_text('0.2.43-rc1\n')
        home = Path(self.temp.name)/'candidate-home'; home.mkdir()
        result = subprocess.run([str(source/'tools/install-control-plane'), str(source)],
                                env={**os.environ, 'HOME':str(home)}, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((home/'.local/share/steamdeck-workstation/releases/0.2.43-rc1/bin/deckctl').exists())
        code = (ROOT/'bootstrap.sh').read_text().split("<<'PY'\n",1)[1].rsplit('\nPY',1)[0]
        namespace = {'__name__':'bootstrap_test'}; exec(compile(code, 'bootstrap', 'exec'), namespace)
        version = '0.2.43-rc1'; repo = namespace['REPO']
        names = [f'steamdeck-workstation-v{version}.tar.gz', f'steamdeck-workstation-v{version}-SHA256SUMS.txt']
        release = {'tag_name':'v'+version, 'prerelease':True,
                   'assets':[{'name':n, 'browser_download_url':f'https://github.com/{repo}/releases/download/v{version}/{n}'} for n in names]}
        namespace['fetch'] = lambda *args:json.dumps(release).encode()
        self.assertEqual(namespace['resolve'](version)[0], version)
        with self.assertRaises(ValueError): namespace['resolve']()

    def test_unattended_failure_tail_redacts_and_logs(self):
        with patch('deckctl.install_log.note') as note, contextlib.redirect_stdout(io.StringIO()) as out:
            with self.assertRaises(RuntimeError):
                run_log.run_step([sys.executable, '-c', 'print("token=fixture-secret"); raise SystemExit(3)'])
        self.assertNotIn('fixture-secret', out.getvalue())
        self.assertIn('<redacted>', out.getvalue())
        self.assertTrue(note.called)

    def test_release_staging_supports_output_on_another_filesystem(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('package_release', ROOT/'tools/package-release.py')
        package = importlib.util.module_from_spec(spec); spec.loader.exec_module(package)
        source = Path(self.temp.name)/'source'; source.mkdir(); (source/'VERSION').write_text('1.2.3-rc1')
        output = Path(self.temp.name)/'different-filesystem'
        replace = os.replace
        def cross_device(src, dst):
            if not Path(src).is_relative_to(output): raise OSError(18, 'Invalid cross-device link')
            return replace(src, dst)
        with patch.object(package, 'ROOT', source), patch.object(sys, 'argv', ['package-release', str(output)]), patch.object(package.subprocess, 'run'), patch('os.replace', side_effect=cross_device), contextlib.redirect_stdout(io.StringIO()):
            package.main()
        self.assertEqual(len(list(output.iterdir())), 3)
        self.assertTrue((output/'steamdeck-workstation-v1.2.3-rc1-SHA256SUMS.txt').is_file())

    def test_network_failure_is_bounded_and_uses_real_repo_endpoint(self):
        import subprocess
        with patch.object(preflight.subprocess, 'run', side_effect=subprocess.TimeoutExpired('curl', 15)) as request:
            rows = preflight.network()
        self.assertEqual([row['status'] for row in rows], ['FAIL']*3)
        urls = [call.args[0][-1] for call in request.call_args_list]
        self.assertIn('https://flathub.org/repo/flathub.flatpakrepo', urls)
        for call in request.call_args_list:
            self.assertEqual(call.kwargs['timeout'], 15)
            self.assertIn('--max-time', call.args[0])

    def test_network_rate_limit_is_actionable_without_blocking_independent_items(self):
        import subprocess
        response = subprocess.CompletedProcess([], 22,
            'HTTP/1.1 200 Connection established\r\n\r\nHTTP/2 403\r\n'
            'x-ratelimit-remaining: 0\r\nx-ratelimit-reset: 1790325901\r\n', '')
        with patch.object(preflight.subprocess, 'run', return_value=response):
            rows = preflight.network()
        self.assertEqual(rows[0]['status'], 'WARN')
        self.assertEqual(rows[1]['status'], 'FAIL')
        self.assertIn('Independent items can continue', rows[0]['message'])
        self.assertIn('rate limit exhausted', rows[0]['message'])
        self.assertIn('08:45:01 UTC', rows[0]['message'])
        self.assertEqual(rows[0]['reset_at'],1790325901)
        self.assertTrue(rows[0]['rate_limited'])
        self.assertNotIn('DNS', rows[0]['message'])
        self.assertIn('HTTP 403', rows[1]['message'])

    def test_ui_rate_limit_uses_saved_preflight_without_network_requests(self):
        from deckctl import setup_window
        with run_log.execution('install') as journal:
            core.save_json(journal.path/'plan.json', {'preflight':{'checks':[{'name':'api.github.com','rate_limited':True,'reset_at':1790325901}]}})
            with patch.object(preflight,'network',side_effect=AssertionError('No API polling')):
                limit = setup_window.Session().github_limit()
            self.assertEqual(limit['resetAt'],1790325901)
            core.save_json(journal.path/'plan.json', {'preflight':{'checks':[]}})
            self.assertIsNone(setup_window.Session().github_limit())

    def test_preflight_warning_continues_but_safety_failure_blocks(self):
        from deckctl import production_cli
        from unittest.mock import Mock
        for status, expected_calls in (('WARN',1),('FAIL',0)):
            callback = Mock(return_value=0)
            report = {'status':status, 'checks':[{'name':'check','status':status,'message':'test'}]}
            with patch.object(preflight,'report',return_value=report), contextlib.redirect_stdout(io.StringIO()):
                result = production_cli.operation('install', callback, check=True)
            self.assertEqual(callback.call_count,expected_calls)
            self.assertEqual(result,0 if expected_calls else 1)

    def test_flatpak_progress_reports_update_and_noop_without_fake_bytes(self):
        from deckctl import flatpak_progress, install_progress
        events = []
        with install_progress.listen(lambda *args: events.append(args)):
            reporter = flatpak_progress.Reporter()
            reporter('Looking for updates…')
            reporter('Updating… █████ 45% 270.2 kB/s 03:59')
            reporter('Nothing to do.')
        self.assertEqual([e[0] for e in events], ['Checking for updates', 'Updating', 'Up to date'])
        self.assertIn('45%', events[1][1])
        self.assertIn('270.2 kB/s', events[1][1])
        self.assertIn('03:59', events[1][1])
        self.assertEqual(events[1][2:], (None, None))

    def test_command_progress_handles_carriage_returns_and_final_fragment(self):
        lines = []
        run_log.run_step([sys.executable, '-c', 'import sys; sys.stdout.write("first\\rsecond\\nlast")'], on_output=lines.append)
        self.assertEqual(lines, ['first', 'second', 'last'])

    def test_flatpak_completion_distinguishes_update_noop_and_system_reuse(self):
        from deckctl import setup_install, setup_plan
        for phase, expected in [('Up to date','Already up to date; verified.'), ('Updating','Updated and verified.')]:
            with patch.object(setup_plan, 'command', return_value='installed-commit'), patch.object(setup_install, '_run', return_value=phase) as run:
                self.assertEqual(setup_install._flatpak('com.discordapp.Discord'), expected)
                run.assert_called_once_with(['flatpak','update','--user','-y','com.discordapp.Discord'])
        with patch.object(setup_plan, 'command', side_effect=['system-commit', None]), patch.object(setup_install, '_run') as run:
            self.assertIn('system installation reused', setup_install._flatpak('com.discordapp.Discord'))
            run.assert_not_called()

    def test_inventory_local_missing_timeout_and_installed(self):
        import subprocess
        from deckctl import setup_inventory
        row = {'key':'app:discord','flatpak':'com.discordapp.Discord'}
        for code, stdout, stderr, status in [(0,'commit','', 'INSTALLED'), (1,'','error: not installed','MISSING')]:
            with patch.object(setup_inventory.subprocess,'run',return_value=subprocess.CompletedProcess([],code,stdout,stderr)):
                self.assertEqual(setup_inventory.local(row)['status'],status)
        for failure in [subprocess.TimeoutExpired('flatpak',8), OSError('missing executable')]:
            with patch.object(setup_inventory.subprocess,'run',side_effect=failure), self.assertRaises(type(failure)):
                setup_inventory.local(row)
        with patch.object(setup_inventory.subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','permission denied')), self.assertRaises(RuntimeError):
            setup_inventory.local(row)
        self.assertFalse(core.STATE.exists())

    def test_inventory_scan_is_nonblocking_and_close_stops_queued_checks(self):
        import threading
        from deckctl import setup_inventory
        release = threading.Event(); entered = threading.Event(); calls = []
        def probe(row):
            calls.append(row['key']); entered.set(); release.wait(2)
            return dict(key=row['key'], installed=False, status='MISSING')
        with patch.object(setup_inventory,'local',side_effect=probe):
            scan = setup_inventory.Scan([{'key':str(i)} for i in range(20)])
            try:
                self.assertTrue(entered.wait(1))
                self.assertTrue(scan.snapshot()['running'])
                scan.close()
                self.assertFalse(scan.snapshot()['running'])
            finally: release.set()
        self.assertLessEqual(len(calls),4)

    def test_inventory_distinguishes_updates_and_failed_update_checks(self):
        from deckctl import setup_inventory, setup_plan
        row = {'key':'app:discord'}
        current = dict(key=row['key'], installed=True, label='Installed')
        for action, check, expected in [('UPDATE','Checked','Update available'), ('UP_TO_DATE','Checked','Up to date'), ('INSTALLED','Unavailable; installer will check','Installed · couldn’t check updates')]:
            with patch.object(setup_plan,'inspect',return_value={'installed':True,'action':action,'updateCheck':check}):
                self.assertEqual(setup_inventory.remote(row,current)['label'],expected)
        self.assertFalse(core.STATE.exists())

    def test_catalog_inventory_does_not_change_saved_choices(self):
        from deckctl import setup_window, setup_inventory
        snapshot = setup_window.Session().snapshot()
        before = json.dumps(snapshot,sort_keys=True)
        rows = setup_inventory.catalog_rows(snapshot)
        self.assertIn('app:discord', {r['key'] for r in rows})
        self.assertEqual(json.dumps(snapshot,sort_keys=True),before)
        self.assertFalse(core.CONFIG_HOME.exists())

    def test_inventory_provider_failure_is_not_missing_and_scan_continues(self):
        from deckctl import setup_inventory
        import time
        def inspect(row):
            if row['key']=='broken': raise OSError('provider unavailable')
            if row['key']=='offline': return dict(key=row['key'], installed=True, label='Installed', status='INSTALLED')
            return dict(key=row['key'], installed=False, label='Not installed', status='MISSING')
        with patch.object(setup_inventory,'local',side_effect=inspect), patch.object(setup_inventory,'remote',side_effect=OSError('offline')):
            scan=setup_inventory.Scan([{'key':'broken'},{'key':'missing'},{'key':'offline'}])
            deadline=time.monotonic()+2
            while scan.snapshot()['running'] and time.monotonic()<deadline: time.sleep(.01)
            result=scan.snapshot(); scan.close()
        self.assertFalse(result['running'])
        self.assertEqual(result['items']['broken']['status'],'UNKNOWN')
        self.assertEqual(result['items']['missing']['status'],'MISSING')
        self.assertTrue(result['items']['offline']['installed'])
        self.assertEqual(result['items']['offline']['label'],'Installed · couldn’t check updates')
        self.assertFalse(core.STATE.exists())


if __name__ == '__main__': unittest.main(verbosity=2)
