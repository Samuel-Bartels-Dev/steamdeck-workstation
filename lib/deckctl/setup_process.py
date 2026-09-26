"""On-demand noninteractive setup process and private, bounded UI output."""
import os
import select
import signal
import secrets
import subprocess
import threading
import time
from . import core, install_log

LIMIT = 65536


def path(): return core.STATE/'setup-console.json'


def snapshot(fingerprint):
    data = core.load_json(path(), {})
    return data if data.get('fingerprint') == fingerprint else {'text':''}


def start(command, fingerprint):
    control_path = core.STATE/('setup-control-'+secrets.token_hex(16)+'.json')
    control = {'pause':False,'cancel':False}
    core.save_json(control_path, control)
    data = {'fingerprint':fingerprint, 'startedAt':time.time(), 'text':'Starting installation…\n', 'exitCode':None}
    core.save_json(path(), data)
    try:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, start_new_session=True,
                                   env=dict(os.environ, DECKCTL_UI_RUN='1', DECKCTL_UI_CONTROL=str(control_path), PYTHONUNBUFFERED='1'))
    except BaseException:
        control_path.unlink(missing_ok=True)
        raise
    finished = threading.Event()
    cancelled_at = None
    class Handle:
        def close(self, grace=5):
            """Stop only this window's process group if its renderer disappears.

            SIGINT gives the installer time to persist its interrupted journal. A
            provider/grandchild ignoring it cannot keep the window owner alive.
            """
            if finished.is_set(): return
            control.update(pause=False, cancel=True)
            try: core.save_json(control_path, control)
            except OSError: pass
            try: os.killpg(process.pid, signal.SIGINT)
            except ProcessLookupError: pass
            # The direct child can exit before grandchildren close inherited pipes.
            finished.wait(grace)
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            finished.wait(2)

        def control(self, action):
            nonlocal cancelled_at
            if action == 'force':
                if process.poll() is not None or cancelled_at is None or time.monotonic()-cancelled_at < 10:
                    raise ValueError('Cancel first and allow ten seconds for the provider to stop.')
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                return dict(control)
            if process.poll() is not None or control['cancel']: raise ValueError('This run has finished or cancellation is already pending.')
            if action not in ('pause','continue','cancel'): raise ValueError('Unknown queue action')
            control.update(pause=action == 'pause', cancel=action == 'cancel')
            core.save_json(control_path, control)
            if action == 'cancel':
                cancelled_at = time.monotonic()
                try: os.killpg(process.pid, signal.SIGINT)
                except ProcessLookupError: pass
            return dict(control)
        def controls(self):
            return dict(control, available=self.poll() is None,
                        forceAvailable=process.poll() is None and cancelled_at is not None and time.monotonic()-cancelled_at >= 10)
        def poll(self): return process.poll() if finished.is_set() else None
        def wait(self, timeout=None):
            if not finished.wait(timeout): raise subprocess.TimeoutExpired(command, timeout)
            return process.returncode
    def collect():
        pending = b''; skipping = False; last = 0; exited = None
        def append(raw):
            clean = install_log.redact(raw.decode('utf-8', errors='replace'))
            if clean.startswith('Run: ') and not data.get('runId'):
                from . import run_log
                run_id = clean.removeprefix('Run: ').strip()
                if run_log.RUN_NAME.fullmatch(run_id):
                    data.update(runId=run_id, logDirectory=str(run_log.root()/run_id),
                                logFile=str(run_log.root()/run_id/install_log.path_for('run:'+run_id).name))
            text = data['text'] + clean + '\n'
            data['text'] = text.encode('utf-8')[-LIMIT:].decode('utf-8', errors='ignore')
            data['lastOutputAt'] = time.time()
        def save():
            data['updatedAt'] = time.time()
            try: core.save_json(path(), data)
            except OSError: pass  # Keep draining a child even if diagnostic storage fills.
        try:
            while True:
                if process.poll() is not None:
                    if exited is None: exited = time.monotonic()
                    elif time.monotonic()-exited > 1: break
                readable = select.select([process.stdout], [], [], .2)[0]
                if readable:
                    chunk = os.read(process.stdout.fileno(), 4096)
                    if not chunk: break
                    pending += chunk.replace(b'\r', b'\n')
                    while b'\n' in pending:
                        line, pending = pending.split(b'\n', 1)
                        if not skipping: append(line)
                        skipping = False
                    if len(pending) > LIMIT:
                        pending = b''; skipping = True
                        append(b'[oversized output line omitted]')
                if time.monotonic()-last >= .5:
                    save(); last = time.monotonic()
            if pending and not skipping: append(pending)
        finally:
            process.stdout.close()
            data['exitCode'] = process.wait()
            # No foreground installer descendant may outlive its owning run.
            # Services started through systemd have their own process group.
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            data['finishedAt'] = time.time()
            try: save()
            finally:
                try: control_path.unlink(missing_ok=True)
                finally: finished.set()
    threading.Thread(target=collect, daemon=True).start()
    return Handle()
