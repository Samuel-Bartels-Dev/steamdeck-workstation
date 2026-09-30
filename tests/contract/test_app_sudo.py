#!/usr/bin/env python3
"""Real IPC/process lifecycle tests with a ppid-scoped sudo stand-in.

No actual sudo, KDE prompt, root operation or installed application is run.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'lib'))
from deckctl import app_sudo, core, setup_process

FAKE = '''#!/usr/bin/env python3
import json, os, pathlib, sys
root=pathlib.Path(os.environ['TEST_SUDO_ROOT'])
ticket=root/('ticket-'+str(os.getppid()))
args=sys.argv[1:]
with (root/'calls').open('a') as out: out.write(json.dumps([os.getppid(),args])+'\\n')
if args==['-k']:
 ticket.unlink(missing_ok=True); sys.exit(0)
if args in (['-A','-v'],['-n','-v']):
 if not ticket.exists():
  if args[0]=='-n': sys.exit(1)
  with (root/'prompts').open('a') as out: out.write('prompt\\n')
  if (root/'cancel').exists(): sys.exit(1)
 ticket.touch(); sys.exit(0)
if args[:2]==['-n','--'] and ticket.exists(): os.execv(args[2],args[2:])
sys.exit(1)
'''


class AppSudo(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(); self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        fake = self.root/'sudo'; fake.write_text(FAKE); fake.chmod(0o700)
        self.env = patch.dict(os.environ, {'TEST_SUDO_ROOT':str(self.root), 'PATH':str(self.root)+os.pathsep+os.environ['PATH']})
        self.env.start(); self.addCleanup(self.env.stop)
        self.owner = app_sudo.Owner(); self.addCleanup(self.owner.close)
        self.client_env = dict(os.environ, **self.owner.environment())

    def client(self, args):
        return subprocess.run([sys.executable, str(app_sudo.HERE/'app_sudo.py'), 'client', *args],
                              env=self.client_env, capture_output=True, text=True, timeout=10)

    def prompts(self):
        path = self.root/'prompts'
        return len(path.read_text().splitlines()) if path.exists() else 0

    def eventually(self, predicate, timeout=8):
        deadline = time.monotonic()+timeout
        while not predicate() and time.monotonic() < deadline: time.sleep(.05)
        self.assertTrue(predicate())

    def test_two_runs_and_provider_subprocess_share_one_ticket_output_and_status(self):
        with patch.object(core, 'STATE', self.root/'state'):
            source = "import subprocess; r=subprocess.run(['sudo','-S',"+repr(sys.executable)+",'-c','import sys; print(\"provider out\"); print(\"provider err\",file=sys.stderr); sys.exit(7)']); raise SystemExit(r.returncode)"
            for fingerprint in ('install','retry','resume'):
                handle = setup_process.start([sys.executable,'-c',source], fingerprint, self.owner)
                self.assertEqual(handle.wait(10),7)
                console = setup_process.snapshot(fingerprint)
                self.assertIn('provider out', console['text']); self.assertIn('provider err', console['text'])
        self.assertEqual(self.prompts(),1)
        calls = [json.loads(line) for line in (self.root/'calls').read_text().splitlines()]
        self.assertEqual({pid for pid, _ in calls}, {self.owner.process.pid})
        self.assertTrue(all('-S' not in args for _, args in calls))

    def test_close_reopen_and_expiry_reauthorize(self):
        self.assertEqual(self.client(['-v']).returncode,0)
        next(self.root.glob('ticket-*')).unlink()
        self.assertEqual(self.client(['-v']).returncode,0)
        self.assertEqual(self.prompts(),2)
        self.owner.close()
        self.assertFalse(list(self.root.glob('ticket-*')))
        self.owner = app_sudo.Owner(); self.addCleanup(self.owner.close)
        self.client_env = dict(os.environ, **self.owner.environment())
        self.assertEqual(self.client(['-v']).returncode,0)
        self.assertEqual(self.prompts(),3)

    def test_noninteractive_provider_check_never_opens_password_dialog(self):
        self.assertNotEqual(self.client(['-n','-v']).returncode,0)
        self.assertEqual(self.prompts(),0)
        self.assertEqual(self.client(['-v']).returncode,0)
        self.assertEqual(self.client(['-n','-v']).returncode,0)
        self.assertEqual(self.prompts(),1)

    def test_long_operation_renews_ticket_without_another_password_dialog(self):
        client = subprocess.Popen([sys.executable,str(app_sudo.HERE/'app_sudo.py'),'client',
                                   sys.executable,'-c','import time; time.sleep(33)'],
                                  env=self.client_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: client.kill() if client.poll() is None else None)
        def renewed():
            path = self.root/'calls'
            return path.exists() and any(json.loads(line)[1] == ['-n','-v'] for line in path.read_text().splitlines())
        self.eventually(renewed, timeout=35)
        self.assertEqual(client.wait(timeout=8),0)
        self.assertEqual(self.prompts(),1)

    def test_helper_crash_kills_command_and_new_owner_cannot_use_old_ticket(self):
        client, pid = self.start_stubborn()
        self.owner.process.kill(); self.owner.process.wait()
        self.eventually(lambda: self.gone(pid)); client.wait(timeout=5)
        self.owner.close()
        self.owner = app_sudo.Owner(); self.addCleanup(self.owner.close)
        self.client_env = dict(os.environ, **self.owner.environment())
        self.assertEqual(self.client(['-v']).returncode,0)
        self.assertEqual(self.prompts(),2)

    def test_successful_command_cannot_leave_detached_privileged_descendant(self):
        pidfile = self.root/'detached-pid'
        child = "import os,signal,time; from pathlib import Path; signal.signal(signal.SIGTERM,signal.SIG_IGN); Path("+repr(str(pidfile))+").write_text(str(os.getpid())); time.sleep(60)"
        parent = "import subprocess,time; from pathlib import Path; subprocess.Popen(["+repr(sys.executable)+",'-c',"+repr(child)+"], start_new_session=True); p=Path("+repr(str(pidfile))+");\nwhile not p.exists(): time.sleep(.01)"
        self.assertEqual(self.client([sys.executable,'-c',parent]).returncode,0)
        self.eventually(lambda: self.gone(int(pidfile.read_text())))

    def test_cancelled_authorization_is_retryable_without_running_command(self):
        (self.root/'cancel').touch()
        result = self.client([sys.executable,'-c',"raise SystemExit('must not run')"])
        self.assertNotEqual(result.returncode,0)
        self.assertIn('cancelled',result.stderr)
        self.assertFalse(list(self.root.glob('ticket-*')))
        (self.root/'cancel').unlink()
        self.assertEqual(self.client(['-v']).returncode,0)

    def test_cancelled_run_cannot_reprompt_or_claim_success_until_retry(self):
        self.client_env['DECKCTL_UI_CONTROL'] = 'first-run'
        (self.root/'cancel').touch()
        self.assertNotEqual(self.client(['-v']).returncode,0)
        (self.root/'cancel').unlink()
        self.assertNotEqual(self.client(['-v']).returncode,0)
        self.assertNotEqual(self.client(['-n','-v']).returncode,0)
        self.assertEqual(self.prompts(),1)
        self.client_env['DECKCTL_UI_CONTROL'] = 'retry-run'
        self.assertEqual(self.client(['-v']).returncode,0)
        self.assertEqual(self.prompts(),2)

    def start_stubborn(self):
        pidfile = self.root/'command-pid'
        source = "import os,signal,time; from pathlib import Path; signal.signal(signal.SIGTERM,signal.SIG_IGN); Path("+repr(str(pidfile))+").write_text(str(os.getpid())); time.sleep(60)"
        client = subprocess.Popen([sys.executable,str(app_sudo.HERE/'app_sudo.py'),'client',sys.executable,'-c',source],
                                  env=self.client_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: client.kill() if client.poll() is None else None)
        self.eventually(pidfile.exists)
        return client, int(pidfile.read_text())

    def gone(self, pid):
        try:
            # Treat a reaped-by-init pending zombie as terminated.
            return Path('/proc/'+str(pid)+'/stat').read_text().split()[2] == 'Z'
        except FileNotFoundError: return True

    def test_cancelled_client_kills_stubborn_privileged_command(self):
        client, pid = self.start_stubborn()
        client.kill(); client.wait()
        self.eventually(lambda: self.gone(pid))
        self.assertEqual(self.client(['-v']).returncode,0)
        self.assertEqual(self.prompts(),1)

    def test_owner_pipe_eof_stops_helper_command_and_ticket(self):
        client, pid = self.start_stubborn()
        # Equivalent to all app fds closing after a crash; no explicit close RPC.
        os.close(self.owner.writer); self.owner.writer = None
        self.assertEqual(self.owner.process.wait(timeout=8),0)
        self.eventually(lambda: self.gone(pid))
        client.wait(timeout=5)
        self.assertFalse(list(self.root.glob('ticket-*')))
        self.assertFalse(Path(self.owner.socket).exists())

    def test_provider_invalidation_or_unknown_flags_fail_closed(self):
        for args in (['-S','-k','-v'], ['-u','root','true'], ['--non-interactive','true']):
            self.assertEqual(self.client(args).returncode,125)
        self.assertEqual(self.prompts(),0)


if __name__ == '__main__': unittest.main()
