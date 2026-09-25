"""Run-scoped sudo authorization; passwords travel only from KDE to sudo."""
from contextvars import ContextVar
import os
from pathlib import Path
import shutil
import subprocess

_authorized = ContextVar('setup_sudo_authorized', default=False)
HELPER = Path(__file__).parent/'ui/sudo-askpass'


def needed(row):
    return row.get('kind') in ('plugin', 'css', 'css-profile')


def command(args):
    if os.environ.get('DECKCTL_UI_RUN') != '1': return ['sudo', *args]
    if not _authorized.get():
        raise RuntimeError('Administrator permission is required. Retry this item to open the password dialog.')
    return ['sudo', '-A', *args]


def environment():
    env = dict(os.environ)
    if os.environ.get('DECKCTL_UI_RUN') == '1': env['SUDO_ASKPASS'] = str(HELPER)
    return env


class Session:
    """Use sudo's session ticket, never retain the password or elevate deckctl."""
    def __enter__(self):
        self.attempted = False
        self.token = _authorized.set(False)
        return self

    def prepare(self):
        from . import preflight
        if not shutil.which('sudo') or not Path('/usr/bin/kdialog').is_file() or not os.access(HELPER, os.X_OK):
            raise RuntimeError('Administrator password dialog is unavailable. Install KDE kdialog and sudo, then retry.')
        if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
            raise RuntimeError('Open setup in Desktop Mode to use the administrator password dialog.')
        readiness = preflight.sudo_readiness()
        if readiness['state'] in ('PASSWORD_MISSING', 'PASSWORD_LOCKED'):
            raise RuntimeError(readiness['message'])
        self.attempted = True
        # No controlling terminal: sudo uses this runner's parent-process ticket
        # under SteamOS's default policy. Start fresh; do not renew in background.
        subprocess.run(['sudo', '-k'], stdin=subprocess.DEVNULL, check=True)
        result = subprocess.run(['sudo', '-A', '-v'], env=environment(), stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, check=False)
        if result.returncode:
            raise RuntimeError('Administrator authorization was cancelled or failed. No administrator steps started. Retry to open the password dialog again.')
        _authorized.set(True)

    def __exit__(self, *_):
        try:
            if self.attempted:
                subprocess.run(['sudo', '-k'], stdin=subprocess.DEVNULL,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5, check=False)
        except (OSError, subprocess.SubprocessError):
            print('Warning: could not invalidate sudo authorization; the operating system timeout still applies.', flush=True)
        finally:
            _authorized.reset(self.token)
