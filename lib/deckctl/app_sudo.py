"""App-owned, unprivileged sudo ticket owner and local subprocess transport.

All sudo invocations have this same parent and no controlling terminal, including
provider calls. sudo owns the temporary ppid ticket; no password enters Python.
An inherited owner pipe ends the helper on app crash as well as normal close.
"""
import array
import json
import os
from pathlib import Path
import select
import shlex
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
SOCKET_ENV = 'DECKCTL_APP_SUDO'
ERROR = 'Administrator authorization was cancelled, expired, or failed. Retry to authorize again.'


class Owner:
    def __init__(self):
        self.directory = tempfile.TemporaryDirectory(prefix='deckctl-app-sudo-')
        self.socket = str(Path(self.directory.name)/'socket')
        shim = Path(self.directory.name)/'sudo'
        shim.write_text('#!/bin/sh\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(HERE/'app_sudo.py'))+' client "$@"\n')
        shim.chmod(0o700)
        reader, self.writer = os.pipe()
        try:
            self.process = subprocess.Popen([sys.executable, str(HERE/'app_sudo.py'), 'serve', self.socket, str(reader)],
                                            pass_fds=(reader,), start_new_session=True,
                                            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except BaseException:
            os.close(self.writer); self.writer = None
            self.directory.cleanup()
            raise
        finally: os.close(reader)
        deadline = time.monotonic()+5
        while not Path(self.socket).exists():
            if self.process.poll() is not None or time.monotonic() > deadline:
                self.close()
                raise RuntimeError('Could not start the app administrator authorization helper.')
            time.sleep(.02)

    def environment(self):
        return {SOCKET_ENV: self.socket, 'PATH':self.directory.name+os.pathsep+os.environ.get('PATH', '')}

    def alive(self):
        return self.process.poll() is None

    def close(self):
        if self.writer is not None:
            os.close(self.writer); self.writer = None
        try: self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            self.process.wait(timeout=5)
        self.directory.cleanup()


def release_session(token, env=None):
    return subprocess.run([sys.executable, str(HERE/'app_sudo.py'), 'client', '--release-session', token],
                          env=env, stdin=subprocess.DEVNULL, check=False).returncode


def client(args):
    path = os.environ.get(SOCKET_ENV)
    if not path:
        print('App administrator authorization is unavailable. Reopen setup.', file=sys.stderr)
        return 125
    # -S is removed: stdin carries command payload only, never authentication.
    # Invalidation flags and arbitrary sudo policy flags fail closed.
    args = list(args)
    noninteractive = False
    while args and args[0] in ('-A', '-S', '-n'):
        noninteractive = noninteractive or args[0] == '-n'
        args.pop(0)
    release = len(args) == 2 and args[0] == '--release-session'
    if args and args[0].startswith('-') and args != ['-v'] and not release:
        print('Unsupported app sudo option. Provider contract needs review.', file=sys.stderr)
        return 125
    request = json.dumps({'args':args, 'cwd':os.getcwd(), 'noninteractive':noninteractive,
                          'run':os.environ.get('DECKCTL_UI_CONTROL'),
                          'keepDescendants':os.environ.get('DECKCTL_SUDO_KEEP_DESCENDANTS') == '1',
                          'session':os.environ.get('DECKCTL_SUDO_SESSION'),
                          'release':args[1] if release else None}).encode()
    with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as connection:
        connection.connect(path)
        connection.sendmsg([request], [(socket.SOL_SOCKET, socket.SCM_RIGHTS, array.array('i', [0, 1, 2]))])
        response = connection.recv(1024)
    return int(response) if response else 125


def serve(path, owner_fd):
    sudo = shutil.which('sudo')
    if not sudo: return 125
    env = dict(os.environ, SUDO_ASKPASS=str(HERE/'ui/sudo-askpass'))
    # Do not accidentally redispatch sudo through the provider shim.
    env.pop(SOCKET_ENV, None)
    active = None
    alive = True
    authorized = False
    last_refresh = 0
    denied_runs = set()
    retained = []
    def stop(*_):
        nonlocal alive
        alive = False
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP): signal.signal(sig, stop)
    def owner_alive():
        return alive and not (select.select([owner_fd], [], [], 0)[0] and not os.read(owner_fd, 1))
    def wait(process, connection=None):
        while process.poll() is None and owner_alive():
            refresh()
            if connection and select.select([connection], [], [], .1)[0]: break
            if not connection: time.sleep(.05)
        return process.poll()
    def invalidate():
        subprocess.run([sudo, '-k'], env=env, stdin=subprocess.DEVNULL,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False)
    def refresh():
        nonlocal authorized, last_refresh
        for item in list(retained):
            if item[0].poll() is not None:
                item[1].close(); retained.remove(item)
        if authorized and time.monotonic()-last_refresh >= 30:
            try:
                authorized = subprocess.run([sudo, '-n', '-v'], env=env, stdin=subprocess.DEVNULL,
                                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5).returncode == 0
            except (OSError, subprocess.SubprocessError): authorized = False
            last_refresh = time.monotonic()
    with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as server:
        server.bind(path); os.chmod(path, 0o600); server.listen(8)
        try:
            invalidate()
            while owner_alive():
                refresh()
                if not select.select([server, owner_fd], [], [], .1)[0] or not owner_alive(): continue
                if not select.select([server], [], [], 0)[0]: continue
                with server.accept()[0] as connection:
                    pid, uid, gid = struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                    if uid != os.getuid(): continue
                    if not select.select([connection, owner_fd], [], [], 2)[0] or not owner_alive(): continue
                    raw, ancillary, flags, _ = connection.recvmsg(65536, socket.CMSG_SPACE(12))
                    fds = array.array('i')
                    for level, kind, value in ancillary:
                        if level == socket.SOL_SOCKET and kind == socket.SCM_RIGHTS: fds.frombytes(value)
                    try:
                        if flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC) or len(fds) != 3: continue
                        request = json.loads(raw)
                        args = request['args']
                        if not isinstance(args, list) or not all(isinstance(a, str) for a in args): continue
                        release = request.get('release')
                        if isinstance(release, str) and release:
                            released = [item for item in retained if item[2] == release]
                            for item in released: item[1].close()
                            for item in released:
                                item[0].wait(timeout=6); retained.remove(item)
                            connection.send(b'0'); continue
                        if args and args[0].startswith('-') and args != ['-v']: continue
                        scope = request.get('run')
                        if scope is not None and not isinstance(scope, str): continue
                        if scope in denied_runs:
                            os.write(fds[2], (ERROR+'\n').encode())
                            connection.send(b'1'); continue
                        # Recheck sudo's real ticket for every request; the boolean
                        # controls renewal only and is never proof of authorization.
                        authorized = False
                        active = subprocess.Popen([sudo, '-n' if request.get('noninteractive') else '-A', '-v'], env=env, stdin=subprocess.DEVNULL,
                                                  stdout=subprocess.DEVNULL, stderr=fds[2], process_group=0)
                        rc = wait(active, connection)
                        if rc is None:
                            os.killpg(active.pid, signal.SIGTERM)
                            try: active.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                os.killpg(active.pid, signal.SIGKILL); active.wait()
                            continue
                        authorized = rc == 0
                        last_refresh = time.monotonic()
                        if rc:
                            if scope and not request.get('noninteractive'): denied_runs.add(scope)
                            os.write(fds[2], (ERROR+'\n').encode())
                        elif args and args != ['-v']:
                            lifetime_path = str(Path(path).parent/('watch-'+str(time.monotonic_ns())))
                            lifetime = None
                            session = request.get('session')
                            keep = request.get('keepDescendants') is True and isinstance(session, str) and bool(session)
                            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as listener:
                                listener.bind(lifetime_path); listener.listen(1)
                                metadata = json.dumps({'command':args, 'cwd':request['cwd'],
                                                       'lifetime':lifetime_path, 'keepDescendants':keep})
                                active = subprocess.Popen([sudo, '-n', '--', sys.executable, str(HERE/'sudo_watch.py'), metadata],
                                                          env=env, stdin=fds[0], stdout=fds[1], stderr=fds[2])
                                try:
                                    deadline = time.monotonic()+5
                                    while active.poll() is None and owner_alive() and time.monotonic() < deadline:
                                        if select.select([listener, connection], [], [], .1)[0]:
                                            if select.select([connection], [], [], 0)[0]: break
                                            lifetime = listener.accept()[0]; break
                                    if lifetime is None:
                                        rc = active.poll()
                                        if rc is None: active.terminate(); rc = active.wait(timeout=5)
                                    else:
                                        response = b''
                                        while active.poll() is None and owner_alive():
                                            refresh()
                                            ready = select.select([lifetime, connection], [], [], .1)[0]
                                            if connection in ready: break
                                            if lifetime in ready:
                                                response += lifetime.recv(1024)
                                                if b'\n' in response: break
                                        rc = int(response.split(b'\n')[0]) if b'\n' in response else active.poll()
                                        if keep and rc == 0 and owner_alive():
                                            retained.append((active, lifetime, session)); lifetime = None
                                finally:
                                    if lifetime is not None: lifetime.close()
                                    Path(lifetime_path).unlink(missing_ok=True)
                                    if not any(item[0] is active for item in retained): active.wait(timeout=6)
                            if rc is None: continue
                        try: connection.send(str(rc if rc >= 0 else 128-rc).encode())
                        except BrokenPipeError: pass
                    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
                        try: connection.send(b'125')
                        except OSError: pass
                    finally:
                        for fd in fds: os.close(fd)
                        active = None
        finally:
            for _, lifetime, _ in retained: lifetime.close()
            for process, _, _ in retained:
                try: process.wait(timeout=6)
                except subprocess.TimeoutExpired: pass
            invalidate()
            Path(path).unlink(missing_ok=True)
    return 0


if __name__ == '__main__':
    try:
        code = serve(sys.argv[2], int(sys.argv[3])) if sys.argv[1] == 'serve' else client(sys.argv[2:])
    except (OSError, ValueError, subprocess.SubprocessError):
        print('App administrator authorization helper stopped. Reopen setup or retry.', file=sys.stderr)
        code = 125
    sys.exit(code)
