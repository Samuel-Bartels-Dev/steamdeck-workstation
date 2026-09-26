"""Locate the logged-in user's systemd runtime without changing GUI variables."""
import os
from pathlib import Path
import stat


def runtime():
    candidate = Path('/run/user') / str(os.getuid())
    try:
        info = candidate.stat()
        bus = candidate/'bus'
        if (not candidate.is_symlink() and info.st_uid == os.getuid() and
                stat.S_ISDIR(info.st_mode) and stat.S_ISSOCK(bus.stat().st_mode) and
                bus.stat().st_uid == os.getuid()):
            return str(candidate)
    except OSError:
        pass
    return os.environ.get('XDG_RUNTIME_DIR')


def environment():
    env = dict(os.environ)
    target = runtime()
    if target:
        env['XDG_RUNTIME_DIR'] = target
        if (Path(target)/'bus').exists(): env['DBUS_SESSION_BUS_ADDRESS'] = 'unix:path='+target+'/bus'
    return env
