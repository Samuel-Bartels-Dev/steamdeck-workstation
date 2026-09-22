"""Private bounded per-item stderr logs; stdout and interactive input stay in Konsole."""
from contextlib import contextmanager
import hashlib
import os
import re
import select
import sys
import threading
import traceback
from . import core
from contextvars import ContextVar

_writer = ContextVar("install_log_writer", default=None)

def note(message):
    writer = _writer.get()
    if writer: writer(message + "\n")

def path_for(key):
    return core.STATE/"install-logs"/(hashlib.sha256(key.encode()).hexdigest()[:24]+".log")

def read(key):
    path = path_for(key)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "r", encoding="utf-8", errors="replace") as stream:
        text = stream.read(LIMIT)
    return redact(text)


LIMIT = 1024 * 1024


def redact(text):
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text)
    text = re.sub(r'(?i)(bearer\s+)\S+', r'\1<redacted>', text)
    text = re.sub(r'(?i)((?:access_token|refresh_token|api[_-]?key|password|secret|token)[\s\"\x27]*[:=][\s\"\x27]*)[^\s\"\x27,;]+', r'\1<redacted>', text)
    text = re.sub(r'(https?://)[^\s/@]+:[^\s/@]+@', r'\1<redacted>@', text)
    return text


@contextmanager
def capture(key):
    directory = core.STATE/'install-logs'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = path_for(key)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as output:
        count = 0
        guard = threading.Lock()
        def save(text):
            with guard: write(text)
        def write(text):
            nonlocal count
            clean = redact(text)
            encoded = clean.encode()[:max(0, LIMIT-count)]
            try:
                output.write(encoded.decode('utf-8', errors='ignore'))
                output.flush()
                count += len(encoded)
            except OSError:
                count = LIMIT  # Logging must not break provider stderr forwarding.
        save('Item: '+key+'\nLast attempt: installer stderr and Python errors. Review before sharing.\n')
        sys.stderr.flush()
        original = os.dup(2)
        reader, writer = os.pipe()
        stop = threading.Event()
        def relay():
            pending = b''
            skipping = False
            drained = 0
            try:
                while True:
                    if stop.is_set():
                        drained += 1
                        if drained > 16: break  # A detached child must not hold up setup.
                    available = select.select([reader], [], [], 0.1)[0]
                    if not available:
                        if stop.is_set(): break
                        continue
                    chunk = os.read(reader, 4096)
                    if not chunk: break
                    try: os.write(original, chunk)
                    except OSError: pass
                    pending += chunk
                    while b'\n' in pending:
                        line, pending = pending.split(b'\n', 1)
                        if not skipping: save(line.decode('utf-8', errors='replace')+'\n')
                        skipping = False
                    if len(pending) > 65536:
                        pending = b''; skipping = True
                if pending and not skipping: save(pending.decode('utf-8', errors='replace'))
            finally:
                os.close(reader)
        thread = threading.Thread(target=relay, daemon=True)
        error = ''
        try:
            os.dup2(writer, 2)
            os.close(writer)
            thread.start()
            token = _writer.set(save)
            try: yield path
            except BaseException:
                error = traceback.format_exc()
                raise
            finally: _writer.reset(token)
        finally:
            sys.stderr.flush()
            os.dup2(original, 2)
            stop.set()
            thread.join()
            os.close(original)
            if error: save('\n'+error)
