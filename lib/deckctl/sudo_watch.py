"""Command supervisor with a separate owner lifetime and command input."""
import ctypes
import json
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import sys
import time


def descendants(pid):
    result = set()
    try:
        tasks = list(Path('/proc/'+str(pid)+'/task').iterdir())
    except FileNotFoundError:
        return result
    for task in tasks:
        try: children = (task/'children').read_text().split()
        except FileNotFoundError: continue
        for child in children:
            child = int(child)
            result.add(child)
            result.update(descendants(child))
    return result


def terminate(sig):
    for pid in descendants(os.getpid()):
        try: os.kill(pid, sig)
        except ProcessLookupError: pass


def cleanup(process):
    # Reap the direct child before the next sweep: its detached children may
    # become ours only when it exits. Repeat for later orphan adoption.
    while True:
        terminate(signal.SIGKILL)
        if process.poll() is None:
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
        process.wait()
        while True:
            try:
                if os.waitpid(-1, os.WNOHANG)[0] == 0: break
            except ChildProcessError: return
        time.sleep(.02)


def main():
    transport = None
    if len(sys.argv) > 1:
        request = json.loads(sys.argv[1])
        transport = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        transport.connect(request['lifetime'])
        lifetime = transport
        command_input = 0
    else:
        header = bytearray()
        while not header.endswith(b'\n'):
            byte = os.read(0, 1)
            if not byte or len(header) > 65536: return 125
            header.extend(byte)
        request = json.loads(header)
        lifetime = 0
        command_input = subprocess.DEVNULL
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'Could not supervise command descendants')
    stopped = None
    def stop(sig, *_):
        nonlocal stopped
        if stopped is None: stopped = (sig, time.monotonic())
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP): signal.signal(sig, stop)
    keep = request.get('keepDescendants') is True
    process = subprocess.Popen(request['command'], cwd=request['cwd'],
                               stdin=command_input, start_new_session=True,
                               stdout=subprocess.PIPE if keep else None,
                               stderr=subprocess.PIPE if keep else None)
    output = {process.stdout:1, process.stderr:2} if keep else {}
    reported = False
    pending_rc = None
    sent_stop = False
    eof_at = None
    try:
        while True:
            for stream in select.select(list(output), [], [], 0)[0] if output else []:
                drained = 0
                while drained < 1048576 and select.select([stream], [], [], 0)[0]:
                    chunk = os.read(stream.fileno(), 4096)
                    if not chunk:
                        stream.close(); del output[stream]; break
                    drained += len(chunk)
                    if not reported:
                        while chunk: chunk = chunk[os.write(output[stream], chunk):]
            rc = process.poll()
            if reported and keep and not descendants(os.getpid()): return rc
            if rc is not None and not reported:
                if keep and pending_rc is None:
                    pending_rc = rc
                    continue  # Drain once more after confirmed direct-child exit.
                if transport: transport.sendall((str(rc)+'\n').encode())
                reported = True
                if not keep or rc != 0: return rc
                # The client may capture output until EOF. Retaining our own
                # descriptors would make a completed startup command hang.
                for fd in (0, 1, 2):
                    try: os.close(fd)
                    except OSError: pass
            if select.select([lifetime], [], [], .1)[0]:
                data = transport.recv(4096) if transport else os.read(0, 4096)
                if not data and eof_at is None:
                    # Owner death or force-close overrides graceful interruption.
                    eof_at = time.monotonic()
                    terminate(getattr(signal, request.get('interrupt', 'SIGTERM')))
            if eof_at is not None:
                if process.poll() is not None or time.monotonic()-eof_at >= 2:
                    return process.poll() if process.poll() is not None else 130
            elif stopped:
                sig, since = stopped
                if not sent_stop:
                    terminate(sig)
                    sent_stop = True
                if process.poll() is not None or time.monotonic()-since >= request.get('grace', 2):
                    return process.poll() if process.poll() is not None else 128+sig
    finally:
        cleanup(process)
        for stream in output: stream.close()
        if transport: transport.close()


if __name__ == '__main__':
    try: code = main()
    except (OSError, ValueError, KeyError): code = 125
    sys.exit(code if code >= 0 else 128-code)
