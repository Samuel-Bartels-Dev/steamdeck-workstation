"""Locate the logged-in user's systemd runtime without changing GUI variables."""
import os
from pathlib import Path
import stat


NESTED_DESKTOP_NOTICE = (
    'Deferred in Nested Desktop: restarting Decky can restart the Steam interface '
    'that hosts this desktop. Switch to normal Desktop Mode yourself, then retry '
    'this item. No session switch or restart was requested.'
)


def nested_desktop():
    """Valve gives the nested session its own nested-desktop.* runtime directory.

    Inspect this process's environment, not stale directories or the systemd
    runtime returned by runtime(), which intentionally points outside nesting.
    """
    return any(part.startswith('nested-desktop.')
               for part in Path(os.environ.get('XDG_RUNTIME_DIR', '')).parts)


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
