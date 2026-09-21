#!/usr/bin/env python3
"""No vendor installs: isolated config, fake engine, real process/HTTP cleanup."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'lib'))
from deckctl import ai_workspace as ai, core, terminal


def alive(pid):
    try:
        # A reparented zombie is no longer executing or retaining model memory.
        return Path(f'/proc/{pid}/stat').read_text().split()[2] != 'Z'
    except FileNotFoundError:
        return False


class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='deckctl-ai-test-')
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.bin = self.home / 'bin'; self.bin.mkdir()
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); self.port = sock.getsockname()[1]
        patches = [(ai, 'HOME', self.home), (ai, 'BIN', self.bin),
                   (ai, 'MODELS', self.home / 'models'), (ai, 'DATA', self.home / 'data'),
                   (ai, 'CONFIG', self.home / 'opencode/config.json'), (ai, 'PORT', self.port),
                   (ai, 'RECEIPT', self.home / 'state/install.json'), (core, 'STATE', self.home / 'state')]
        for obj, name, value in patches:
            p = patch.object(obj, name, value); p.start(); self.addCleanup(p.stop)
        fake = self.bin / 'ollama'
        fake.write_text(f'''#!{sys.executable}
import json,os,sys,time,subprocess
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
root=Path({str(self.home)!r})
if sys.argv[1]=='serve':
    child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(90)'])
    (root/'pids.json').write_text(json.dumps([os.getpid(),child.pid]))
    (root/'env.json').write_text(json.dumps(dict(os.environ)))
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200);self.end_headers();self.wfile.write(b'{{"version":"test"}}')
        def log_message(self,*args): pass
    HTTPServer(('127.0.0.1',int(os.environ['OLLAMA_HOST'].rsplit(':',1)[1])),Handler).serve_forever()
if sys.argv[1]=='pull':
    if (root/'fail-pull').exists(): sys.exit(4)
    models=Path(os.environ['OLLAMA_MODELS']);digest='sha256:'+('a'*64)
    manifest=models/'manifests/registry.ollama.ai/library/qwen2.5-coder/1.5b'
    manifest.parent.mkdir(parents=True,exist_ok=True)
    (models/'blobs').mkdir(exist_ok=True)
    (models/'blobs'/digest.replace(':','-')).write_bytes(b'test')
    manifest.write_text(json.dumps({{'config':{{'digest':digest,'size':4}},'layers':[]}}))
''')
        fake.chmod(0o755)

    def free_port(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            return sock.getsockname()[1]

    def assert_stopped(self):
        pids = json.loads((self.home / 'pids.json').read_text())
        deadline = time.monotonic() + 3
        while any(alive(p) for p in pids) and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertFalse(any(alive(p) for p in pids), pids)

    def test_owned_server_and_runners_stop_on_client_failure(self):
        with ai.server():
            self.assertTrue(ai.occupied())
            self.assertEqual(ai.run_client([sys.executable, '-c', 'raise SystemExit(7)']), 7)
            env = json.loads((self.home / 'env.json').read_text())
            self.assertEqual(env['OLLAMA_KEEP_ALIVE'], '0')
            self.assertEqual(env['OLLAMA_HOST'], f'127.0.0.1:{self.port}')
            self.assertEqual(env['OLLAMA_MODELS'], str(ai.MODELS))
        self.assert_stopped()
        self.assertFalse(ai.occupied())

    def test_existing_endpoint_is_never_borrowed_or_stopped(self):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', self.port)); sock.listen()
            with self.assertRaisesRegex(RuntimeError, 'already in use'):
                with ai.server():
                    self.fail('should not start')
            self.assertFalse((self.home / 'pids.json').exists())
            self.assertEqual(sock.getsockname()[1], self.port)

    def test_concurrent_workspace_refused(self):
        with ai.server():
            with self.assertRaisesRegex(RuntimeError, 'already owns'):
                with ai.server():
                    self.fail('should not start')
        self.assert_stopped()

    def test_pull_downloads_then_shuts_down_and_failed_pull_also_cleans_up(self):
        ai.PORT = self.free_port()
        ai.pull()
        self.assertTrue(ai.model_present()); self.assert_stopped()
        (self.home / 'fail-pull').touch()
        ai.PORT = self.free_port()
        with self.assertRaisesRegex(RuntimeError, 'download failed'):
            ai.pull()
        self.assert_stopped()

    def test_sigterm_cleanup_in_supervisor(self):
        code = f'''import sys,time
sys.path.insert(0,{str(ROOT / 'lib')!r})
from pathlib import Path
from deckctl import ai_workspace as ai,core
ai.BIN=Path({str(self.bin)!r});ai.PORT={self.port}
core.STATE=Path({str(self.home / 'state')!r})
with ai.server(): time.sleep(90)
'''
        process = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 8
            while not (self.home / 'pids.json').exists() and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue((self.home / 'pids.json').exists())
            process.send_signal(signal.SIGTERM); process.wait(timeout=8)
            self.assert_stopped()
        finally:
            if process.poll() is None:
                process.kill(); process.wait()

    def test_foreground_client_reads_terminal_and_restores_group(self):
        import pty
        import select
        pid, fd = pty.fork()
        if pid == 0:
            try:
                old = os.tcgetpgrp(0)
                result = ai.run_client([sys.executable, '-c', 'print("CLIENT_READY",flush=True); print(input(),flush=True)'])
                ok = result == 0 and os.tcgetpgrp(0) == old
                os._exit(0 if ok else 2)
            except BaseException:
                os._exit(3)
        try:
            output = b''
            deadline = time.monotonic() + 5
            while b'CLIENT_READY' not in output and time.monotonic() < deadline:
                if select.select([fd], [], [], .1)[0]:
                    output += os.read(fd, 4096)
            self.assertIn(b'CLIENT_READY', output)
            os.write(fd, b'hello\n')
            while time.monotonic() < deadline:
                ended, result = os.waitpid(pid, os.WNOHANG)
                if ended:
                    self.assertEqual(os.waitstatus_to_exitcode(result), 0)
                    pid = None
                    break
                time.sleep(.02)
            self.assertIsNone(pid, 'foreground client failed to exit')
        finally:
            os.close(fd)
            if pid is not None:
                os.kill(pid, signal.SIGKILL); os.waitpid(pid, 0)

    def test_config_preserves_user_values_and_rejects_conflicts_atomically(self):
        ai.CONFIG.parent.mkdir()
        ai.CONFIG.write_text(json.dumps({'theme': 'personal', 'provider': {'other': {'name': 'Keep'}}}))
        ai.configure(); before = ai.CONFIG.read_bytes(); ai.configure()
        self.assertEqual(ai.CONFIG.read_bytes(), before)
        data = json.loads(before)
        self.assertEqual(data['theme'], 'personal')
        self.assertIn('other', data['provider'])
        self.assertNotIn('access_token', data)
        data['provider']['local-ollama']['options']['baseURL'] = 'http://elsewhere'
        ai.CONFIG.write_text(json.dumps(data)); before = ai.CONFIG.read_bytes()
        with self.assertRaises(ValueError): ai.configure()
        self.assertEqual(ai.CONFIG.read_bytes(), before)

    def test_status_is_readonly_and_cloud_profile_never_starts_local_engine(self):
        before = sorted(str(p) for p in self.home.rglob('*'))
        with contextlib.redirect_stdout(io.StringIO()): ai.status(True)
        self.assertEqual(sorted(str(p) for p in self.home.rglob('*')), before)
        ai.configure()
        from argparse import Namespace
        args = Namespace(ai_command='open', profile='chatgpt-pro', model='openai/test-model')
        with patch.object(ai, 'server') as server, patch.object(ai, 'run_client', return_value=0) as client:
            self.assertEqual(ai.dispatch(args), 0)
            server.assert_not_called()
            self.assertEqual(client.call_args.args[0][-1], 'openai/test-model')

    def test_archive_traversal_and_escaping_symlinks_rejected(self):
        for name, target in [('../escape', None), ('lib/ollama/link', '../../../../outside')]:
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode='w') as tar:
                info = tarfile.TarInfo(name)
                if target:
                    info.type = tarfile.SYMTYPE; info.linkname = target; tar.addfile(info)
                else:
                    info.size = 1; tar.addfile(info, io.BytesIO(b'x'))
            buf.seek(0)
            with tarfile.open(fileobj=buf) as tar, self.assertRaises(ValueError):
                ai._extract(tar, self.home / 'extract')
        self.assertFalse((self.home / 'escape').exists())

    def test_appimage_digest_and_failed_version_preserve_old_wrapper(self):
        with patch.object(terminal, 'HOME', self.home), patch.object(terminal, 'BIN_DIR', self.bin):
            binary = self.bin / 'nvim'; binary.write_text('old')
            data = b'#!/bin/sh\nexit 1\n'
            asset = {'name': 'nvim.appimage', 'browser_download_url': 'https://test', 'digest': 'sha256:' + hashlib.sha256(data).hexdigest()}
            with patch.object(terminal, '_github_asset', return_value=({'tag_name': 'test'}, asset)), patch.object(terminal, '_request', return_value=data):
                with self.assertRaisesRegex(RuntimeError, 'version check'):
                    terminal._install_appimage('test/repo', '.*', 'nvim')
            self.assertEqual(binary.read_text(), 'old')
            asset['digest'] = 'sha256:bad'
            with patch.object(terminal, '_github_asset', return_value=({'tag_name': 'test'}, asset)), patch.object(terminal, '_request', return_value=data):
                with self.assertRaisesRegex(RuntimeError, 'SHA-256'):
                    terminal._install_appimage('test/repo', '.*', 'nvim')
            self.assertEqual(binary.read_text(), 'old')


if __name__ == '__main__':
    unittest.main(verbosity=2)
