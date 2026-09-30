"""Narrow command supervisor: stdin EOF revokes a running command, even as root.

Invoked by sudo, never by the UI. The pipe contains command metadata, not secrets.
Commands using this interface are noninteractive; GUI interaction stays visible.
"""
import json
import ctypes
import os
import select
import signal
import subprocess
import sys
import time
from pathlib import Path


def descendants(pid):
    result = []
    try: children = Path('/proc/'+str(pid)+'/task/'+str(pid)+'/children').read_text().split()
    except FileNotFoundError: return result
    for child in children:
        result.append(int(child)); result.extend(descendants(int(child)))
    return result


def terminate(sig):
    for pid in reversed(descendants(os.getpid())):
        try: os.kill(pid, sig)
        except ProcessLookupError: pass


def main():
    # Unbuffered read avoids consuming the lifetime pipe beyond the header.
    header = bytearray()
    while not header.endswith(b'\n'):
        byte = os.read(0, 1)
        if not byte or len(header) > 65536: return 125
        header.extend(byte)
    request = json.loads(header)
    # Adopt orphaned grandchildren, including those creating a separate session.
    # Services explicitly handed to systemd remain owned by systemd.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0: raise OSError(ctypes.get_errno(), 'Could not supervise command descendants')
    process = subprocess.Popen(request['command'], cwd=request['cwd'],
                               stdin=subprocess.DEVNULL, start_new_session=True)
    stopped = False
    def stop(*_):
        nonlocal stopped
        stopped = True
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP): signal.signal(sig, stop)
    try:
        while process.poll() is None and not stopped:
            if select.select([0], [], [], .1)[0] and not os.read(0, 4096): break
        if process.poll() is None:
            terminate(signal.SIGTERM)
            deadline = time.monotonic() + 2
            while process.poll() is None and time.monotonic() < deadline: time.sleep(.05)
        return process.wait() if process.poll() is not None else 130
    finally:
        # Also remove descendants when their immediate parent has exited.
        try: os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        terminate(signal.SIGKILL)
        process.wait()
        while True:
            try: os.waitpid(-1, 0)
            except ChildProcessError: break


if __name__ == '__main__':
    try: code = main()
    except (OSError, ValueError, KeyError): code = 125
    sys.exit(code if code >= 0 else 128-code)
