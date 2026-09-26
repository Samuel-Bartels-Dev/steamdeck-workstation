"""Private bounded per-item stdout/stderr logs, preserving terminal forwarding."""
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
def capture(key, stdout=True):
    directory = core.STATE/'install-logs'
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = path_for(key)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w+', encoding='utf-8') as output:
        count = 0
        guard = threading.Lock()
        def save(text):
            with guard: write(text)
        def write(text):
            nonlocal count
            clean = redact(text)
            encoded = clean.encode()[-LIMIT:]
            try:
                if count + len(encoded) > LIMIT:
                    output.seek(0)
                    previous = output.read().encode()
                    # Drop whole old lines, retaining recent diagnostics within the cap.
                    room = min(LIMIT//2, max(0, LIMIT-len(encoded)))
                    keep = previous[-room:] if room else b''
                    keep = keep.partition(b'\n')[2]
                    output.seek(0); output.truncate()
                    output.write(keep.decode('utf-8', errors='ignore'))
                    count = len(keep)
                output.write(encoded.decode('utf-8', errors='ignore'))
                output.flush()
                count += len(encoded)
            except OSError:
                count = LIMIT  # Logging must not break provider stderr forwarding.
        save('Item: '+key+'\nLast attempt: '+('stdout, ' if stdout else '')+'stderr and Python errors. Review before sharing.\n')
        sys.stdout.flush(); sys.stderr.flush()
        originals = {number: os.dup(number) for number in ((1, 2) if stdout else (2,))}
        pipes = {number: os.pipe() for number in originals}
        stop = threading.Event()
        def relay(number):
            reader = pipes[number][0]
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
                    try: os.write(originals[number], chunk)
                    except OSError: pass
                    pending += chunk.replace(b'\r', b'\n')
                    while b'\n' in pending:
                        line, pending = pending.split(b'\n', 1)
                        if not skipping: save(line.decode('utf-8', errors='replace')+'\n')
                        skipping = False
                    if len(pending) > 65536:
                        pending = b''; skipping = True
                        save('[oversized output line omitted]\n')
                if pending and not skipping: save(pending.decode('utf-8', errors='replace'))
            finally:
                os.close(reader)
        threads = [threading.Thread(target=relay, args=(number,), daemon=True) for number in originals]
        error = ''
        try:
            for number, (_, writer) in pipes.items():
                os.dup2(writer, number)
                os.close(writer)
            for thread in threads: thread.start()
            token = _writer.set(save)
            try: yield path
            except BaseException:
                error = traceback.format_exc()
                raise
            finally: _writer.reset(token)
        finally:
            sys.stdout.flush(); sys.stderr.flush()
            for number, original in originals.items(): os.dup2(original, number)
            stop.set()
            for thread in threads: thread.join()
            for original in originals.values(): os.close(original)
            if error: save('\n'+error)
