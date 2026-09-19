#!/usr/bin/env python3
"""Offline container integration contracts; CI additionally runs real Docker/Compose."""
import contextlib
import io
import json
import os
from pathlib import Path
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
        with patch.object(c, 'status_data', return_value={'status': 'READY'}), patch.object(c, 'docker', side_effect=[result(1), result()]) as docker:
            self.assertEqual(c.smoke(), 1)
        first, last = [call.args[0] for call in docker.call_args_list]
        self.assertEqual(first[2], last[2])
        self.assertTrue(first[2].startswith('deckctl-test-'))
        self.assertIn('down', last)
        self.assertNotIn('--volumes', last)

    def test_smoke_asserts_real_response_and_cleans(self):
        with patch.object(c, 'status_data', return_value={'status': 'READY'}), patch.object(c, 'docker', side_effect=[result(), result(output='wrong'), result()]):
            self.assertEqual(c.smoke(), 1)
        with patch.object(c, 'status_data', return_value={'status': 'READY'}), patch.object(c, 'docker', side_effect=[result(), result(output='deckctl-container-ok\n'), result()]):
            self.assertEqual(c.smoke(), 0)

    def test_smoke_timeout_still_attempts_cleanup(self):
        with patch.object(c, 'status_data', return_value={'status': 'READY'}), patch.object(c, 'docker', side_effect=[subprocess.TimeoutExpired('docker', 1), result()]) as docker:
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
        with contextlib.redirect_stdout(io.StringIO()) as output, patch.object(c, 'status_data', return_value={'status': 'READY'}), patch.object(c, 'docker', side_effect=[failed, result()]) as docker:
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
