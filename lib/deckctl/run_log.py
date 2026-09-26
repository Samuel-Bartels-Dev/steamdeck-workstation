"""Bounded, private run journals. No daemon; flock protects live runs from cleanup."""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import time
from . import core, install_log

_current = ContextVar('deckctl_run', default=None)
RUN_NAME = re.compile(r'^[a-z]+-\d{8}T\d{6}-[0-9a-f]{12}$')
LIMIT = 4 * 1024 * 1024


def root(): return core.STATE / 'logs'


def safe(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Log path contains a symlink')


def read_json(path):
    safe(path)
    if path.stat().st_size > LIMIT: raise ValueError('Oversized run record')
    return json.loads(path.read_text())


def runs():
    safe(root())
    result = []
    if not root().exists(): return result
    for path in sorted(root().iterdir(), reverse=True):
        if not RUN_NAME.fullmatch(path.name) or path.is_symlink() or not path.is_dir(): continue
        try:
            record = read_json(path/'result.json')
            if (not isinstance(record, dict) or record.get('run_id') != path.name
                    or record.get('status') not in ('PASS','WARN','FAIL','RUNNING')
                    or record.get('operation') not in ('install','repair','update','test','apply')
                    or not isinstance(record.get('started_at'), (int,float))): continue
            record['directory'] = str(path)
            result.append(record)
        except (OSError, ValueError, TypeError): continue
    return sorted(result, key=lambda row: row.get('started_at', 0), reverse=True)


class Run:
    def __init__(self, operation):
        if operation not in ('install', 'repair', 'update', 'test', 'apply'): raise ValueError('Invalid run operation')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
        self.id = f'{operation}-{stamp}-{secrets.token_hex(6)}'
        safe(root())
        root().mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = root()/self.id
        self.path.mkdir(mode=0o700)
        self.lock = (self.path/'active.lock').open('w')
        os.chmod(self.path/'active.lock', 0o600)
        fcntl.flock(self.lock, fcntl.LOCK_EX)
        self.started = time.monotonic()
        self.result = {'schema_version': 1, 'run_id': self.id, 'operation': operation,
                       'status': 'RUNNING', 'started_at': time.time(),
                       'version': (core.ROOT/'VERSION').read_text().strip()}
        core.save_json(self.path/'result.json', self.result)
        self.event('run', 'INFO', 'RUNNING', 'Run started')

    def event(self, module, severity, status, message, **fields):
        entry = {'timestamp': datetime.now(timezone.utc).isoformat(), 'run_id': self.id,
                 'module': module, 'severity': severity, 'operation': self.result['operation'],
                 'status': status, 'message': str(message), **fields}
        def scrub(value):
            if isinstance(value, str): return install_log.redact(value)
            if isinstance(value, dict): return {k: scrub(v) for k,v in value.items()}
            if isinstance(value, list): return [scrub(v) for v in value]
            return value
        line = json.dumps(scrub(entry), ensure_ascii=True) + '\n'
        for name, text in [('events.jsonl', line), ('run.log', install_log.redact(
                f"{entry['timestamp']} {self.id} [{module}] {severity} {status}: {message}\n"))]:
            path = self.path/name
            with path.open('a', encoding='utf-8') as stream:
                os.chmod(path, 0o600)
                if stream.tell() + len(text.encode()) <= LIMIT:
                    stream.write(text)

    def finish(self, code):
        self.result.update(status='PASS' if code == 0 else 'WARN' if code == 2 else 'FAIL',
                           exit_code=code, finished_at=time.time(),
                           duration_ms=round((time.monotonic()-self.started)*1000))
        self.event('run', 'INFO' if code == 0 else 'ERROR', self.result['status'], 'Run finished',
                   duration_ms=self.result['duration_ms'])
        core.save_json(self.path/'result.json', self.result)


@contextmanager
def execution(operation):
    existing = _current.get()
    if existing:
        yield existing
        return
    run = Run(operation)
    token = _current.set(run)
    try:
        yield run
    except BaseException:
        run.finish(1)
        raise
    finally:
        if run.result['status'] == 'RUNNING': run.finish(1)
        _current.reset(token)
        run.lock.close()
        clean()


def event(module, status, message, **fields):
    run = _current.get()
    if run: run.event(module, 'ERROR' if status in ('FAILED', 'BLOCKED', 'INTERRUPTED') else 'INFO', status, message, **fields)


def archive_item(key):
    run = _current.get()
    if not run: return
    source = install_log.path_for(key)
    if not source.exists(): return
    safe(source)
    destination = run.path / source.name
    destination.write_text(install_log.read(key))
    destination.chmod(0o600)


def clean(all_runs=False, now=None):
    """Never remove live runs, newest failure, or unrecognized/user files."""
    now = time.time() if now is None else now
    rows = runs()
    newest_failure = next((r['run_id'] for r in rows if r['status'] in ('FAIL', 'WARN', 'RUNNING')), None)
    counts = {}
    removed = []
    for row in rows:
        op = row['operation']; counts[op] = counts.get(op, 0) + 1
        if row['run_id'] == newest_failure: continue
        if not all_runs:
            if row['status'] in ('FAIL', 'WARN', 'RUNNING') and now-row['started_at'] < 30*86400: continue
            if counts[op] <= (10 if op in ('install', 'apply', 'test') else 5): continue
        path = Path(row['directory']); safe(path)
        with (path/'active.lock').open('r') as lock:
            try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError: continue
            allowed = {'active.lock', 'result.json', 'events.jsonl', 'run.log', 'plan.json'}
            children = list(path.iterdir())
            if any(p.is_symlink() or not p.is_file() or
                   (p.name not in allowed and not re.fullmatch(r'[0-9a-f]{24}\.log', p.name)) for p in children): continue
            for p in children: p.unlink()
            path.rmdir(); removed.append(path.name)
    return removed


def command(action, module=None, all_runs=False):
    if action == 'clean':
        for name in clean(all_runs): print('Removed '+name)
        return 0
    rows = runs()
    if action == 'list':
        for row in rows: print(row['run_id'], row['status'], row['directory'])
        return 0
    if not rows:
        print('No recorded runs.'); return 0
    path = Path(rows[0]['directory'])
    if action == 'latest': print(path); return 0
    source = path/'events.jsonl'
    safe(source)
    with source.open() as stream:
        for line in stream:
            data = json.loads(line)
            if action == 'errors' and data['severity'] != 'ERROR': continue
            if action == 'show' and data['module'] != module: continue
            print(install_log.redact(line).rstrip())
    return 0


def run_step(args, env=None, verbose=False, on_output=None):
    """Capture unattended command output; interactive providers keep their own terminal."""
    import subprocess
    from collections import deque
    recent = deque(maxlen=20)
    with subprocess.Popen(args, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT) as process:
        try:
            pending = b''
            while True:
                chunk = process.stdout.read1(4096)
                if not chunk: break
                pending += chunk.replace(b'\r', b'\n')
                while b'\n' in pending:
                    line, pending = pending.split(b'\n', 1)
                    text = install_log.redact(line.decode('utf-8', errors='replace'))
                    recent.append(text[-2000:])
                    if not verbose: install_log.note(text)
                    if on_output: on_output(text)
                    if verbose: print(text, flush=True)
                if len(pending) > 65536:
                    install_log.note('[oversized provider line omitted]'); pending = b''
            if pending:
                text = install_log.redact(pending.decode('utf-8', errors='replace'))
                recent.append(text[-2000:])
                if verbose: print(text, flush=True)
                else: install_log.note(text)
                if on_output: on_output(text)
            code = process.wait()
        except BaseException:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
            raise
    if code:
        print('Last command output:\n'+'\n'.join(recent))
        raise RuntimeError(f'Unattended installer exited with code {code}; inspect the item/run log.')
