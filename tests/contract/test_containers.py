#!/usr/bin/env python3
"""Offline container integration contracts; CI additionally runs real Docker/Compose."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'lib'))
from deckctl import containers as c


def result(code=0, output=''):
    return subprocess.CompletedProcess([], code, output, 'fixture error' if code else '')


class Containers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.base = self.home / 'containers'
        self.cfg = self.home / 'config/containers.json'
        self.unit = self.home / 'systemd/deckctl-docker.service'
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(c, 'paths', return_value=(self.base, self.cfg, self.unit)))
        self.stack.enter_context(patch.object(Path, 'home', return_value=self.home))
        self.stack.enter_context(patch.dict(os.environ, {'XDG_RUNTIME_DIR': str(self.home)}))
        self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))

    def save(self, value):
        c.core.save_json(self.cfg, value)

    def test_status_is_read_only_and_never_starts(self):
        with patch.object(c, 'execute') as command:
            self.assertEqual(c.status_data()['status'], 'NOT_CONFIGURED')
            command.assert_not_called()
        self.assertFalse(self.cfg.exists())
        self.assertFalse(self.base.exists())

    def test_missing_prerequisites_do_not_download_or_write(self):
        with patch.object(c.os, 'geteuid', return_value=1000), patch.object(c.shutil, 'which', return_value=None), patch.object(c, 'prerequisites', return_value=['missing newuidmap']), patch.object(c, 'download') as download:
            self.assertEqual(c.install(), 2)
            download.assert_not_called()
        self.assertFalse(self.base.exists())

    def test_existing_docker_requires_explicit_adoption(self):
        with patch.object(c.os, 'geteuid', return_value=1000), patch.object(c.shutil, 'which', return_value='/usr/bin/docker'), patch.object(c, 'prerequisites') as pre:
            self.assertEqual(c.install(), 2)
            pre.assert_not_called()
        self.assertFalse(self.cfg.exists())

    def test_context_adoption_preserves_daemon_and_global_config(self):
        with patch.object(c.os, 'geteuid', return_value=1000), patch.object(c, 'docker', return_value=result()), patch.object(c, 'smoke', return_value=0), patch.object(c, 'execute') as command:
            self.assertEqual(c.install(context='default'), 0)
            command.assert_not_called()
        self.assertEqual(json.loads(self.cfg.read_text())['context'], 'default')
        self.assertFalse(self.unit.exists())

    def test_bad_context_not_persisted(self):
        with patch.object(c.os, 'geteuid', return_value=1000), patch.object(c, 'docker', return_value=result(1)):
            self.assertEqual(c.install(context='missing'), 2)
        self.assertFalse(self.cfg.exists())

    def test_managed_client_ignores_ambient_remote_endpoint(self):
        with patch.dict(os.environ, {'DOCKER_HOST': 'tcp://unwanted:2375', 'DOCKER_CONTEXT': 'wrong'}):
            command, env = c.client({'mode': 'managed', 'runtime': 'v1'})
        self.assertIn('unix://' + str(self.home) + '/deckctl-docker.sock', command)
        self.assertNotIn('DOCKER_HOST', env)
        self.assertNotIn('DOCKER_CONTEXT', env)
        self.assertEqual(env['DOCKER_CONFIG'], str(self.base / 'client'))

    def test_remote_client_uses_explicit_ssh_without_global_context_change(self):
        command, env = c.client({'mode': 'remote', 'runtime': 'v1', 'remote': 'ssh://deck@host'})
        self.assertEqual(command[-1], 'ssh://deck@host')
        self.assertEqual(env['DOCKER_CONFIG'], str(self.base / 'client'))
        self.assertFalse(self.cfg.exists())

    def test_context_engine_cannot_be_stopped_or_enabled(self):
        self.save({'mode': 'context', 'context': 'default'})
        with patch.object(c, 'execute') as command:
            for action in (lambda: c.service('stop'), lambda: c.autostart('on')):
                with self.assertRaises(ValueError):
                    action()
            command.assert_not_called()

    def test_managed_status_rejects_rootful_endpoint(self):
        self.save({'mode': 'managed', 'runtime': 'v1'})
        with patch.object(c, 'docker', side_effect=[result(output='{"SecurityOptions": []}'), result(output='5.5.1')]), patch.object(c, 'execute', return_value=result(output='disabled')):
            self.assertEqual(c.status_data()['status'], 'CONFIG_REQUIRED')

    def engine_status(self, engine='one', driver='overlayfs', code=0):
        info = json.dumps({'ID': engine, 'ServerVersion': '29.8.1', 'Driver': driver,
                           'SecurityOptions': ['name=rootless']})
        with patch.object(c, 'docker', side_effect=[result(code, info), result(output='5.5.1')]), patch.object(c, 'execute', return_value=result(output='disabled')):
            return c.status_data()

    def test_api_response_is_not_container_readiness_and_status_never_writes(self):
        self.save({'mode': 'managed', 'runtime': 'v1'})
        before = self.cfg.read_bytes()
        data = self.engine_status()
        self.assertEqual(data['status'], 'API_READY')
        self.assertTrue(data['api_ready'])
        self.assertEqual(data['test_status'], 'NOT_RUN')
        self.assertFalse(c.test_receipt_path().exists())
        self.assertEqual(self.cfg.read_bytes(), before)

    def test_saved_result_matches_engine_storage_and_live_api(self):
        self.save({'mode': 'managed', 'runtime': 'v1'})
        data = self.engine_status()
        c.core.save_json(c.test_receipt_path(), {'identity': data['test_identity'], 'result': 'PASSED', 'at': 'test-time'})
        before = c.test_receipt_path().read_bytes()
        self.assertEqual(self.engine_status()['status'], 'READY')
        self.assertEqual(self.engine_status(engine='two')['status'], 'API_READY')
        self.assertEqual(self.engine_status(driver='fuse-overlayfs')['status'], 'API_READY')
        self.assertEqual(self.engine_status(code=1)['status'], 'STOPPED_OR_UNREACHABLE')
        self.assertEqual(c.test_receipt_path().read_bytes(), before)
        for outcome, expected in [('FAILED', 'TEST_FAILED'), ('RUNNING', 'TEST_REQUIRED')]:
            c.core.save_json(c.test_receipt_path(), {'identity': data['test_identity'], 'result': outcome, 'failure': 'overlay_mount'})
            self.assertEqual(self.engine_status()['status'], expected)

    def test_smoke_persists_http_and_cleanup_outcomes(self):
        api = {'api_ready': True, 'test_identity': 'fixture'}
        cases = [(result(output='deckctl-container-ok'), result(), 0, 'PASSED'),
                 (result(output='wrong'), result(), 1, 'FAILED'),
                 (result(output='deckctl-container-ok'), result(1), 1, 'FAILED')]
        for probe, cleanup, code, outcome in cases:
            with patch.object(c, 'status_data', return_value=api), patch.object(c, 'docker', side_effect=[result(), probe, cleanup]):
                self.assertEqual(c.smoke(), code)
            receipt = json.loads(c.test_receipt_path().read_text())
            self.assertEqual(receipt['result'], outcome)
            self.assertEqual(receipt['identity'], 'fixture')
            self.assertTrue(receipt['at'])
        with patch.object(c, 'status_data', return_value=api), patch.object(c, 'docker', side_effect=[subprocess.TimeoutExpired('docker', 1), result()]):
            with self.assertRaises(subprocess.TimeoutExpired):
                c.smoke()
        self.assertEqual(json.loads(c.test_receipt_path().read_text())['result'], 'FAILED')

    def test_service_start_waits_for_api_without_requiring_prior_test(self):
        self.save({'mode': 'managed'})
        with patch.object(c, 'prerequisites', return_value=[]), patch.object(c, 'execute', return_value=result()), patch.object(c, 'status_data', return_value={'api_ready': True, 'status': 'API_READY'}):
            self.assertEqual(c.service('start'), 0)

    def test_guided_overlay_repair_accepts_only_empty_managed_engine(self):
        self.save({'mode': 'managed'})
        with patch.object(c, 'smoke', return_value=1), patch.object(c, 'status_data', return_value={'test_failure': 'overlay_mount'}), patch.object(c.shutil, 'which', return_value='/usr/bin/fuse-overlayfs'), patch.object(c.os, 'isatty', return_value=True), patch('builtins.input', return_value='yes'), patch.object(c, 'docker', return_value=result()), patch.object(c, 'service', return_value=0) as service, patch.object(c, 'install', return_value=0) as install:
            self.assertEqual(c.install_test(), 0)
            service.assert_called_once_with('stop')
            install.assert_called_once_with(storage_driver='fuse-overlayfs')

    def test_guided_repair_decline_missing_helper_noninteractive_and_workloads_do_not_stop(self):
        self.save({'mode': 'managed'})
        for interactive, helper, answer, inventory in [(False, 'helper', 'yes', [result()]),
                                                       (True, None, 'yes', [result()]),
                                                       (True, 'helper', 'no', [result()]),
                                                       (True, 'helper', 'yes', [result(output='user-container')]),
                                                       (True, 'helper', 'yes', [result(1)]),
                                                       (True, 'helper', 'yes', [result(), result(output='new-container')])]:
            with self.subTest(interactive=interactive, helper=helper, answer=answer), patch.object(c, 'smoke', return_value=1), patch.object(c, 'status_data', return_value={'test_failure': 'overlay_mount'}), patch.object(c.shutil, 'which', return_value=helper), patch.object(c.os, 'isatty', return_value=interactive), patch('builtins.input', return_value=answer), patch.object(c, 'docker', side_effect=inventory), patch.object(c, 'service') as service, patch.object(c, 'install') as install:
                self.assertEqual(c.install_test(), 2)
                service.assert_not_called()
                install.assert_not_called()

    def test_guided_repair_does_not_touch_remote_or_retry_fuse_failures(self):
        for settings in ({'mode': 'remote'}, {'mode': 'context'}, {'mode': 'managed', 'storage_driver': 'fuse-overlayfs'}):
            self.save(settings)
            with patch.object(c, 'smoke', return_value=1), patch.object(c, 'status_data', return_value={'test_failure': 'overlay_mount'}), patch.object(c, 'service') as service:
                self.assertEqual(c.install_test(), 1)
                service.assert_not_called()

    def archive(self, name, kind=None):
        file = self.home / 'test.tar'
        with tarfile.open(file, 'w') as tar:
            item = tarfile.TarInfo(name)
            if kind:
                item.type = kind
                item.linkname = '/tmp/outside'
                tar.addfile(item)
            else:
                item.size = 4
                tar.addfile(item, io.BytesIO(b'test'))
        return file

    def test_archive_traversal_links_and_unexpected_layout_rejected(self):
        dest = self.home / 'extract'
        dest.mkdir()
        for name, kind in [('docker/../../escape', None), ('docker/tool', tarfile.SYMTYPE), ('docker/tool', tarfile.LNKTYPE), ('wrong/tool', None), ('/absolute', None)]:
            with self.subTest(name=name, kind=kind), self.assertRaises(ValueError):
                c.unpack(self.archive(name, kind), dest)
        self.assertEqual(list(dest.iterdir()), [])

    def test_valid_archive_extracts_executable(self):
        dest = self.home / 'extract'
        dest.mkdir()
        c.unpack(self.archive('docker/docker'), dest)
        self.assertEqual((dest / 'docker').read_bytes(), b'test')
        self.assertTrue(os.access(dest / 'docker', os.X_OK))

    def test_bad_checksum_rejected(self):
        response = io.BytesIO(b'bad asset')
        with patch.object(c.urllib.request, 'urlopen', return_value=response), self.assertRaisesRegex(ValueError, 'checksum'):
            c.download({'url': 'https://download.docker.com/test', 'sha256': '0' * 64}, self.home / 'download')

    def test_smoke_health_failure_cleans_only_own_project(self):
        with patch.object(c, 'status_data', return_value={'status': 'API_READY', 'api_ready': True, 'test_identity': 'fixture'}), patch.object(c, 'docker', side_effect=[result(1), result()]) as docker:
            self.assertEqual(c.smoke(), 1)
        first, last = [call.args[0] for call in docker.call_args_list]
        self.assertEqual(first[2], last[2])
        self.assertTrue(first[2].startswith('deckctl-test-'))
        self.assertIn('down', last)
        self.assertNotIn('--volumes', last)

    def test_smoke_asserts_real_response_and_cleans(self):
        with patch.object(c, 'status_data', return_value={'status': 'API_READY', 'api_ready': True, 'test_identity': 'fixture'}), patch.object(c, 'docker', side_effect=[result(), result(output='wrong'), result()]):
            self.assertEqual(c.smoke(), 1)
        with patch.object(c, 'status_data', return_value={'status': 'API_READY', 'api_ready': True, 'test_identity': 'fixture'}), patch.object(c, 'docker', side_effect=[result(), result(output='deckctl-container-ok\n'), result()]):
            self.assertEqual(c.smoke(), 0)

    def test_smoke_timeout_still_attempts_cleanup(self):
        with patch.object(c, 'status_data', return_value={'status': 'API_READY', 'api_ready': True, 'test_identity': 'fixture'}), patch.object(c, 'docker', side_effect=[subprocess.TimeoutExpired('docker', 1), result()]) as docker:
            with self.assertRaises(subprocess.TimeoutExpired):
                c.smoke()
            self.assertIn('down', docker.call_args_list[-1].args[0])

    def test_declined_provisioning_stays_skipped_but_install_can_opt_in(self):
        self.save({'opt_in': False})
        with patch.object(c, 'install') as install:
            self.assertEqual(c.provision(), 0)
            install.assert_not_called()

    def test_noninteractive_unselected_provision_has_no_state_writes(self):
        with patch.object(c.os, 'isatty', return_value=False), patch.object(c, 'install') as install:
            self.assertEqual(c.provision(), 0)
            install.assert_not_called()
        self.assertFalse(self.cfg.exists())

    def test_opted_in_provision_retries_install(self):
        self.save({'opt_in': True})
        with patch.object(c, 'install', return_value=2) as install:
            self.assertEqual(c.provision(), 2)
            install.assert_called_once()

    def test_saved_tool_checkbox_controls_provision_without_second_prompt(self):
        with patch.object(c.core, 'CONFIG_HOME', self.home/'choices'), patch.object(c.core, 'enabled_modules', return_value=['dev']), patch.object(c.core, 'topo', return_value=['base','dev']), patch('builtins.input', side_effect=AssertionError('No second opt-in')):
            c.core.save_json(c.core.CONFIG_HOME/'components.json', {'dev':[]})
            with patch.object(c, 'install') as install:
                self.assertEqual(c.provision(),0)
                install.assert_not_called()
            c.core.save_json(c.core.CONFIG_HOME/'components.json', {'dev':['docker']})
            self.save({'opt_in':False})
            with patch.object(c, 'install',return_value=0) as install:
                self.assertEqual(c.provision(),0)
                install.assert_called_once()

    def test_unit_escaping_and_no_system_boot_enable(self):
        text = c.unit_text(Path('/home/a space%/bin'))
        self.assertIn('a space%%/bin', text)
        self.assertIn('--data-root=', text)
        self.assertNotIn('sudo', text)
        self.assertNotIn('enable-linger', text)
        self.assertIn('WantedBy=default.target', text)

    def test_fuse_requires_helper_before_any_changes(self):
        self.save({'mode': 'managed', 'runtime': 'v1'})
        before = self.cfg.read_bytes()
        with patch.object(c.os, 'geteuid', return_value=1000), patch.object(c, 'prerequisites', return_value=[]), patch.object(c.shutil, 'which', return_value=None), patch.object(c, 'download') as download:
            self.assertEqual(c.install(storage_driver='fuse-overlayfs'), 2)
            download.assert_not_called()
        self.assertEqual(self.cfg.read_bytes(), before)
        self.assertFalse(self.unit.exists())

    def test_storage_switch_does_not_restart_running_engine(self):
        self.save({'mode': 'managed', 'runtime': 'v1'})
        before = self.cfg.read_bytes()
        with patch.object(c.os, 'geteuid', return_value=1000), patch.object(c, 'prerequisites', return_value=[]), patch.object(c.shutil, 'which', return_value='/usr/bin/fuse-overlayfs'), patch.object(c, 'execute', return_value=result()), patch.object(c, 'service') as service:
            self.assertEqual(c.install(storage_driver='fuse-overlayfs'), 2)
            service.assert_not_called()
        self.assertEqual(self.cfg.read_bytes(), before)
        self.assertFalse(self.unit.exists())

    def test_storage_override_cannot_modify_remote_or_context(self):
        with patch.object(c.os, 'geteuid', return_value=1000), patch.object(c, 'execute') as execute:
            for kwargs in ({'remote': 'ssh://user@host'}, {'context': 'default'}):
                with self.assertRaises(ValueError):
                    c.install(storage_driver='fuse-overlayfs', **kwargs)
            self.save({'mode': 'remote', 'remote': 'ssh://user@host'})
            with self.assertRaises(ValueError):
                c.install(storage_driver='fuse-overlayfs')
            execute.assert_not_called()

    def test_overlay_failure_explains_repair_and_still_cleans(self):
        self.save({'mode': 'managed', 'runtime': 'v1'})
        failed = subprocess.CompletedProcess([], 1, '', 'fstype: overlay, err: invalid argument')
        with contextlib.redirect_stdout(io.StringIO()) as output, patch.object(c, 'status_data', return_value={'status': 'API_READY', 'api_ready': True, 'test_identity': 'fixture'}), patch.object(c, 'docker', side_effect=[failed, result()]) as docker:
            self.assertEqual(c.smoke(), 1)
            self.assertIn('--storage-driver fuse-overlayfs', output.getvalue())
            self.assertIn('down', docker.call_args_list[-1].args[0])

    def test_cleanup_never_prunes(self):
        self.base.mkdir()
        keep = self.base / 'database'
        keep.write_text('private')
        with patch.object(c, 'docker') as docker:
            self.assertEqual(c.cleanup(), 0)
            docker.assert_not_called()
        self.assertEqual(keep.read_text(), 'private')

    def test_aliases_require_configuration_without_writes(self):
        self.assertEqual(c.aliases(), 2)
        self.assertFalse((self.home / '.bashrc').exists())

    def test_aliases_preserve_shell_files_and_repeat_without_changes(self):
        self.save({'mode': 'managed', 'runtime': 'v1'})
        rc = self.home / '.bashrc'
        rc.write_text('export MY_SETTING=keep\n')
        rc.chmod(0o640)
        self.assertEqual(c.aliases(), 0)
        before = rc.read_bytes(), rc.stat().st_mtime_ns
        self.assertEqual(c.aliases(), 0)
        self.assertEqual((rc.read_bytes(), rc.stat().st_mtime_ns), before)
        self.assertEqual(rc.stat().st_mode & 0o777, 0o640)
        self.assertIn('export MY_SETTING=keep', rc.read_text())
        self.assertEqual(rc.read_text().count('# >>> steamdeck-workstation Docker aliases >>>'), 1)
        target = self.home / 'custom-shell'
        target.write_text('preserve')
        (self.home / '.zshrc').unlink()
        (self.home / '.zshrc').symlink_to(target)
        with self.assertRaises(ValueError):
            c.aliases()
        self.assertEqual(target.read_text(), 'preserve')

    def test_aliases_execute_in_real_shells_and_preserve_native_commands(self):
        self.save({'mode': 'managed', 'runtime': 'v1'})
        c.aliases()
        bindir = self.home / 'bin'
        bindir.mkdir()
        stub = bindir / 'deckctl'
        stub.write_text(f'#!{sys.executable}\nimport json,os,sys\nprint(json.dumps([sys.argv[1:],os.getcwd()]))\nsys.exit(int(os.environ.get("ALIAS_TEST_EXIT", "0")))\n')
        stub.chmod(0o755)
        script = self.home / 'commands.sh'
        project = self.home / 'project with spaces'
        project.mkdir()
        env = {**os.environ, 'HOME': str(self.home), 'PATH': str(bindir)}
        source = '. "$HOME/.config/deckctl/shell/containers.sh"\n'
        cases = [('docker ps -a', ['docker', '--', 'ps', '-a']),
                 ('d logs --tail 20 demo', ['docker', '--', 'logs', '--tail', '20', 'demo']),
                 ('docker compose up -d', ['docker', '--', 'compose', 'up', '-d']),
                 ('docker buildx version', ['docker', '--', 'buildx', 'version']),
                 ('docker-compose up -d', ['compose', '--', 'up', '-d']),
                 ('compose -f "file with spaces.yml" config', ['compose', '--', '-f', 'file with spaces.yml', 'config']),
                 ("dc run app echo '$(literal)'", ['compose', '--', 'run', 'app', 'echo', '$(literal)'])]
        for shell_name in ('bash', 'zsh'):
            shell = shutil.which(shell_name)
            if not shell:
                continue
            flags = ['--noprofile', '--norc'] if shell_name == 'bash' else ['-f']
            prelude = 'shopt -s expand_aliases\n' if shell_name == 'bash' else ''
            for invocation, expected in cases:
                with self.subTest(shell=shell_name, command=invocation):
                    script.write_text(prelude + source + source + invocation + '\n')
                    output = subprocess.run([shell, *flags, str(script)], env=env, cwd=project, capture_output=True, text=True)
                    self.assertEqual(output.returncode, 0, output.stderr)
                    self.assertEqual(json.loads(output.stdout), [['containers', *expected], str(project)])
            script.write_text(prelude + source + 'dc ps\n')
            output = subprocess.run([shell, *flags, str(script)], env={**env, 'ALIAS_TEST_EXIT': '17'}, capture_output=True)
            self.assertEqual(output.returncode, 17)
            native = bindir / 'docker'
            native.write_text('#!/bin/sh\nprintf "native\\n"\n')
            native.chmod(0o755)
            script.write_text(prelude + "alias dc='printf custom-alias'\ncompose() { printf custom-function; }\n" + source + 'docker ps\nprintf "\\n"\ndc ps\nprintf "\\n"\ncompose ps\n')
            output = subprocess.run([shell, *flags, str(script)], env=env, capture_output=True, text=True)
            self.assertEqual(output.returncode, 0, output.stderr)
            self.assertEqual(output.stdout.split(), ['native', 'custom-alias', 'custom-function'])
            native.unlink()

    def test_managed_install_writes_private_state_and_repeats_without_download(self):
        def fake_download(asset, target):
            if target.name in ('compose', 'buildx'):
                target.write_bytes(b'plugin')
            else:
                names = ('docker', 'dockerd') if target.name == 'engine' else ('rootlesskit', 'dockerd-rootless.sh')
                with tarfile.open(target, 'w') as tar:
                    for name in names:
                        item = tarfile.TarInfo('docker/' + name)
                        item.size = 4
                        tar.addfile(item, io.BytesIO(b'tool'))
        with patch.object(c.os, 'geteuid', return_value=1000), patch.object(c.shutil, 'which', return_value=None), patch.object(c, 'prerequisites', return_value=[]), patch.object(c, 'download', side_effect=fake_download) as download, patch.object(c, 'execute', return_value=result()), patch.object(c, 'service', return_value=0), patch.object(c, 'smoke', return_value=0):
            self.assertEqual(c.install(), 0)
            count = download.call_count
            self.assertEqual(c.install(), 0)
            self.assertEqual(download.call_count, count)
            # An explicit repair keeps old storage intact and persists across retries.
            old_data = self.base / 'data/containerd/keep'
            old_data.parent.mkdir(parents=True)
            old_data.write_text('existing image data')
            with patch.object(c.shutil, 'which', return_value='/usr/bin/fuse-overlayfs'), patch.object(c, 'execute', side_effect=lambda args, **kw: result(3) if 'is-active' in args else result()):
                self.assertEqual(c.install(storage_driver='fuse-overlayfs'), 0)
                repaired = self.unit.read_text()
                self.assertIn('--feature=containerd-snapshotter=false', repaired)
                self.assertIn('--storage-driver=fuse-overlayfs', repaired)
                self.assertEqual(c.install(), 0)
                self.assertEqual(self.unit.read_text(), repaired)
                self.assertEqual(c.config()['storage_driver'], 'fuse-overlayfs')
                self.assertEqual(old_data.read_text(), 'existing image data')
                self.assertEqual(download.call_count, count)
                self.assertEqual(c.install(storage_driver='default'), 0)
                self.assertNotIn('--storage-driver=', self.unit.read_text())
                self.assertNotIn('--feature=', self.unit.read_text())
                self.assertNotIn('storage_driver', c.config())
                self.assertEqual(old_data.read_text(), 'existing image data')
        self.assertEqual(c.config()['mode'], 'managed')
        self.assertTrue(self.unit.read_text().startswith(c.MARKER))
        self.assertTrue((self.base / 'client/cli-plugins/docker-buildx').is_file())
        self.assertFalse(list((self.base / 'runtime').glob('.download-*')))
        self.assertFalse((self.unit.parent / 'default.target.wants').exists())

    def test_failed_download_leaves_no_config_or_service_or_cache(self):
        with patch.object(c.os, 'geteuid', return_value=1000), patch.object(c.shutil, 'which', return_value=None), patch.object(c, 'prerequisites', return_value=[]), patch.object(c, 'download', side_effect=ValueError('checksum')):
            with self.assertRaisesRegex(ValueError, 'checksum'):
                c.install()
        self.assertFalse(self.cfg.exists())
        self.assertFalse(self.unit.exists())
        self.assertEqual(list((self.base / 'runtime').iterdir()), [])

    def test_invalid_remote_and_root_are_rejected_before_writes(self):
        with patch.object(c.os, 'geteuid', return_value=1000):
            for endpoint in ('tcp://host:2375', 'ssh://user:password@host', 'ssh://-oProxyCommand=bad', 'ssh://user@host/path'):
                with self.assertRaises(ValueError):
                    c.install(remote=endpoint)
        with patch.object(c.os, 'geteuid', return_value=0), self.assertRaises(ValueError):
            c.install()
        self.assertFalse(self.cfg.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
