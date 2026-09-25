"""On-demand noninteractive setup process and private, bounded UI output."""
import os
import select
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
    data = {'fingerprint':fingerprint, 'startedAt':time.time(), 'text':'Starting installation…\n', 'exitCode':None}
    core.save_json(path(), data)
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, start_new_session=True,
                               env=dict(os.environ, DECKCTL_UI_RUN='1', PYTHONUNBUFFERED='1'))
    finished = threading.Event()
    class Handle:
        def poll(self): return process.poll() if finished.is_set() else None
        def wait(self, timeout=None):
            if not finished.wait(timeout): raise subprocess.TimeoutExpired(command, timeout)
            return process.returncode
    def collect():
        pending = b''; skipping = False; last = 0; exited = None
        def append(raw):
            text = data['text'] + install_log.redact(raw.decode('utf-8', errors='replace')) + '\n'
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
            data['finishedAt'] = time.time()
            try: save()
            finally: finished.set()
    threading.Thread(target=collect, daemon=True).start()
    return Handle()
