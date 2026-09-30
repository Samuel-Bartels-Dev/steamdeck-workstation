from __future__ import annotations

import json
import hashlib
from contextlib import contextmanager
import os
import shutil
import shlex
import subprocess
import tempfile
import threading
from pathlib import Path

HOME = Path.home()
CHECKOUT = HOME / 'steamos-waydroid-bundle'
IMAGE = HOME / 'Android_Waydroid/waydroid.img'
STATE = HOME / '.local/share/waydroid'
LEGACY = HOME / 'waydroid'
SHORTCUT_HELPER = HOME / 'Android_Waydroid/steam-shortcuts.py'
LAUNCHER = HOME / 'Android_Waydroid/Android_Waydroid_Cage.sh'

# Inspected provider 6f643fb42afc0595a7c8fe1d6f3350b748c8001c.
# Only the files whose contracts we adapt are pinned, not the bundle catalog.
PROVIDER_CONTRACT = {
    'steamos-waydroid-installer.sh': '7f1c36f3666f7e149e180f58d09470b336ba11138ef9d137f28b1145c5b7bd0a',
    'libexec/steamos-waydroid/installer-sanity-checks.sh': '2a6bb23ec4a4338d619888a36ea2ab1dfa1f3d8bd42e44433771ba79b32f8279',
}
AUTH_START = '\tIFS= read -r -s -p "Please enter current sudo password: " current_password\n'
AUTH_END = "\tprintf 'Sudo authentication succeeded.\\n'\n"
INSTALLER_ROOT = "printf '%s\\n' \"$WORKING_DIR\" >~/Android_Waydroid/installer-root"
LAUNCHER_DIGEST = '08a8cda7d23059976bc061c603a636cabfea2918f6de2c3ded6901e92136970d'


@contextmanager
def _app_provider():
    """Adapt only inspected authentication, output and password-required rules.

    The original checkout is untouched. Compatibility, bundle/fingerprint,
    storage, protected-repair and GUI image selection remain upstream code.
    """
    for relative, digest in PROVIDER_CONTRACT.items():
        source = CHECKOUT/relative
        if not source.is_file() or source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise RuntimeError('Android provider contract changed: '+relative+'. No provider changes were run; the app adapter needs review.')
    with tempfile.TemporaryDirectory(prefix='deckctl-android-provider-') as directory:
        staged = Path(directory)/'provider'
        shutil.copytree(CHECKOUT, staged, ignore=shutil.ignore_patterns('.git', 'logfile', 'logfile-test'))
        sanity = staged/'libexec/steamos-waydroid/installer-sanity-checks.sh'
        text = sanity.read_text()
        start, end = text.index(AUTH_START), text.index(AUTH_END)+len(AUTH_END)
        text = text[:start]+("\t# No password is read or passed to this provider.\n"
                            "\tcurrent_password=''\n"
                            "\tif ! sudo -v; then\n"
                            "\t\tprintf 'App administrator authorization failed; Retry in setup.\\n' >&2\n"
                            "\t\treturn 1\n\tfi\n")+text[end:]
        sanity.write_text(text)
        installer = staged/'steamos-waydroid-installer.sh'
        # The installed Toolbox must point back to the original checkout, not a
        # temporary adapter that disappears when this installation returns.
        installer.write_text(installer.read_text().replace(INSTALLER_ROOT,
                             "printf '%s\\n' "+shlex.quote(str(CHECKOUT))+" >~/Android_Waydroid/installer-root"))
        # Upstream ships runtime NOPASSWD rules. Do not add persistent password
        # bypasses through this app: retain the commands with PASSWD instead.
        rules = staged/'extras/zzzzzzzz-waydroid'
        expected = ''.join('deck ALL=(root) NOPASSWD: /usr/bin/'+name+'\n' for name in
                           ('waydroid-startup-scripts', 'waydroid-shutdown-scripts', 'waydroid-mount', 'waydroid-firewall'))
        if rules.read_text() != expected:
            raise RuntimeError('Android provider sudoers contract changed. Adapter needs review; nothing was installed.')
        rules.write_text(expected.replace('NOPASSWD:', 'PASSWD:'))
        version = subprocess.run(['git', '-C', str(CHECKOUT), 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, check=True)
        (staged/'.source-version').write_text(version.stdout.strip()+'\n')
        yield staged


@contextmanager
def _provider_output(directory):
    """Forward upstream's redirected privileged-step log to the shared console."""
    stopped = threading.Event()
    def follow():
        offset = 0
        while True:
            path = directory/'logfile'
            if path.is_file():
                with path.open('rb') as stream:
                    stream.seek(offset)
                    raw = stream.read()
                    offset = stream.tell()
                if raw:
                    from . import install_log
                    print(install_log.redact(raw.decode('utf-8', errors='replace')), end='', flush=True)
            if stopped.wait(.1):
                # Final drain happens on the next loop before exit.
                if path.is_file():
                    with path.open('rb') as stream:
                        stream.seek(offset)
                        raw = stream.read()
                    if raw:
                        from . import install_log
                        print(install_log.redact(raw.decode('utf-8', errors='replace')), end='', flush=True)
                return
    thread = threading.Thread(target=follow, daemon=True); thread.start()
    try: yield
    finally: stopped.set(); thread.join(timeout=2)


@contextmanager
def _app_launcher():
    if not os.environ.get('DECKCTL_APP_SUDO'):
        raise RuntimeError('App administrator authorization is unavailable. Reopen setup.')
    if hashlib.sha256(LAUNCHER.read_bytes()).hexdigest() != LAUNCHER_DIGEST:
        raise RuntimeError('Installed Android launcher contract changed. App adapter needs review; the existing image was not changed.')
    with tempfile.TemporaryDirectory(prefix='deckctl-android-launch-') as directory:
        target = Path(directory)/LAUNCHER.name
        text = LAUNCHER.read_text()
        text = text.replace('SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"',
                            'SCRIPT_DIR='+shlex.quote(str(LAUNCHER.parent)))
        text = text.replace('>"$LAUNCH_ERROR_LOG" 2>&1', '> >(tee "$LAUNCH_ERROR_LOG") 2>&1')
        # Mirror error guidance into the console and keep the provider GUI visible.
        text = text.replace('kdialog --error', 'deckctl_launch_error --error')
        text = text.replace('set -Eeuo pipefail', "set -Eeuo pipefail\ndeckctl_launch_error() { printf '%s\\n' \"$2\" >&2; kdialog \"$@\"; }")
        target.write_text(text); target.chmod(0o700)
        yield target


def _state_present():
    return STATE.exists() or LEGACY.exists()


def ready():
    # Steam shortcut visibility is deliberately NOT part of Android readiness.
    # Steam may not commit shortcuts.vdf synchronously while running in Desktop Mode.
    return IMAGE.is_file() and _state_present()


def _shortcut_count():
    if not SHORTCUT_HELPER.is_file():
        return None
    try:
        result = subprocess.run(
            ['python3', str(SHORTCUT_HELPER), 'count', 'waydroid'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
            check=False,
        )
        value = result.stdout.strip()
        if result.returncode == 0 and value.isdigit():
            return int(value)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _shortcut_state():
    count = _shortcut_count()
    if count is None:
        return 'UNKNOWN'
    if count > 0:
        return 'FOUND'
    if ready():
        return 'PENDING_STEAM_REFRESH'
    return 'NOT_READY'


def status(json_mode=False):
    data = {
        'checkout_present': (CHECKOUT / '.git').exists(),
        'image_present': IMAGE.is_file(),
        'user_state_present': _state_present(),
        'ready': ready(),
        'shortcut_state': _shortcut_state(),
        'recommended': 'Android 13 with Google Play',
    }
    if json_mode:
        print(json.dumps(data, indent=2))
    else:
        print('Android / Waydroid\n------------------')
        print(f"Installer checkout : {'FOUND' if data['checkout_present'] else 'MISSING'}")
        print(f"Android image      : {'FOUND' if data['image_present'] else 'MISSING'}")
        print(f"Android user state : {'FOUND' if data['user_state_present'] else 'MISSING'}")
        print(f"Game Mode shortcut : {data['shortcut_state']}")
        print(f"Overall            : {'READY' if data['ready'] else 'CONFIG_REQUIRED'}")
        print('Recommended        : Android 13 with Google Play')
        if data['image_present'] and not data['user_state_present']:
            print('Next step          : deckctl android retry opens the bundled launcher for first-run setup.')
        if data['shortcut_state'] == 'PENDING_STEAM_REFRESH':
            print('Note               : Android is installed; switch to Game Mode/restart Steam to refresh the shortcut.')
    return 0 if data['ready'] else 2


def _ensure_checkout():
    if (CHECKOUT / '.git').exists():
        return True
    if not shutil.which('git'):
        print('git is required to fetch the SteamOS Waydroid installer.')
        return False
    return subprocess.run(
        ['git', 'clone', '--depth=1', 'https://github.com/pjohno/steamos-waydroid-bundle.git', str(CHECKOUT)]
    ).returncode == 0


def _write_nonblocking_steam_shim(directory: Path, real_add: str) -> Path:
    """Shadow steamos-add-to-steam so upstream Steam URI submissions cannot own our terminal.

    The real helper may launch a full Steam process when Steam is not already ready in
    Desktop Mode.  The upstream Waydroid installer calls it synchronously, so that Steam
    process can keep the entire installer attached indefinitely.  We detach only this
    shortcut submission; upstream still performs its own bounded shortcut polling.
    """
    shim = directory / 'steamos-add-to-steam'
    quoted = real_add.replace("'", "'\\''")
    shim.write_text(
        '#!/usr/bin/env bash\n'
        'set -u\n'
        f"real='{quoted}'\n"
        'if command -v setsid >/dev/null 2>&1; then\n'
        '  setsid -f "$real" "$@" </dev/null >/dev/null 2>&1 || true\n'
        'else\n'
        '  nohup "$real" "$@" </dev/null >/dev/null 2>&1 &\n'
        'fi\n'
        'exit 0\n'
    )
    shim.chmod(0o755)
    return shim


def _run(mode=None):
    from . import user_session
    if user_session.nested_desktop():
        print(user_session.NESTED_DESKTOP_NOTICE, flush=True)
        return 2
    if not _ensure_checkout():
        return 1
    if os.environ.get('DECKCTL_UI_RUN') == '1':
        if not os.environ.get('DECKCTL_APP_SUDO'):
            print('Android CONFIG_REQUIRED: reopen setup to obtain app administrator authorization.')
            return 2
        try:
            with _app_provider() as staged:
                return _run_provider(staged, mode)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            print('Android CONFIG_REQUIRED: '+str(exc), flush=True)
            return 2
    return _run_provider(CHECKOUT, mode)


def _run_provider(checkout, mode):
    cmd = [str(checkout / 'steamos-waydroid-installer.sh')]
    if mode:
        cmd.append(mode)
    print('Launching SteamOS Waydroid installer.')
    print('For a fresh install choose: Android 13 with Google Play.')
    print('Administrator operations use the app authorization.' if os.environ.get('DECKCTL_UI_RUN') == '1'
          else 'The upstream installer may request your sudo password for host integration.')
    print('Follow the visible Android image chooser. Progress and verification continue here.', flush=True)
    print('Steam shortcut creation is detached so Steam cannot keep this setup terminal open.')

    env = os.environ.copy()
    real_add = shutil.which('steamos-add-to-steam')
    with _provider_output(checkout):
        if not real_add:
            rc = subprocess.run(cmd, cwd=checkout, env=env).returncode
        else:
            with tempfile.TemporaryDirectory(prefix='deckctl-waydroid-') as tmp:
                shim_dir = Path(tmp)
                _write_nonblocking_steam_shim(shim_dir, real_add)
                env['PATH'] = f"{shim_dir}:{env.get('PATH', '')}"
                rc = subprocess.run(cmd, cwd=checkout, env=env).returncode

    if rc != 0:
        return rc
    if not _app_authorization_result(): return 2
    if IMAGE.is_file() and not _state_present():
        return _first_run()

    # The Android install/repair is authoritative. Shortcut visibility may lag until
    # Steam refreshes; report that separately instead of converting success to failure.
    if rc == 0 and ready():
        shortcut = _shortcut_state()
        print('Waydroid verification: PASS (image + Android user state present).')
        if shortcut == 'PENDING_STEAM_REFRESH':
            print('Game Mode shortcut: PENDING STEAM REFRESH (no reinstall required).')
        elif shortcut == 'FOUND':
            print('Game Mode shortcut: FOUND')
        else:
            print(f'Game Mode shortcut: {shortcut}')
        return 0
    print('Android CONFIG_REQUIRED: installer completed but image/user state is incomplete.')
    return 2


def _app_authorization_result():
    # A provider may suppress a failed sudo call in shell cleanup. Never let an
    # authentication cancellation turn into successful Android completion.
    if os.environ.get('DECKCTL_UI_RUN') != '1': return True
    from . import privilege
    result = subprocess.run(privilege.command(['-n','-v']), env=privilege.environment(), stdin=subprocess.DEVNULL, check=False)
    if result.returncode:
        print('Android CONFIG_REQUIRED: administrator authorization failed or was cancelled. Retry here; existing Android state is preserved.', flush=True)
        return False
    return True


def _first_run():
    """Use the vendor launcher that mounts the existing image before opening Android."""
    from . import user_session
    if user_session.nested_desktop():
        print(user_session.NESTED_DESKTOP_NOTICE, flush=True)
        return 2
    if not IMAGE.is_file() or not LAUNCHER.is_file() or not os.access(LAUNCHER, os.X_OK):
        print('Android CONFIG_REQUIRED: bundled launcher/image missing; run deckctl android repair.')
        return 2
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        print('Android CONFIG_REQUIRED: first launch requires Desktop Mode. Run deckctl android retry there.')
        return 2
    print('Opening the installed Android image with its bundled Waydroid launcher.', flush=True)
    print('Complete Android/Google Play sign-in if prompted, then close Android to resume provisioning.', flush=True)
    try:
        if os.environ.get('DECKCTL_UI_RUN') == '1':
            with _app_launcher() as launcher:
                rc = subprocess.run([str(launcher)], cwd=LAUNCHER.parent).returncode
        else:
            rc = subprocess.run([str(LAUNCHER)], cwd=LAUNCHER.parent).returncode
    except (OSError, RuntimeError) as exc:
        print(f'Android launcher failed: {exc}')
        return 2
    if rc != 0:
        print(f'Android launcher exited with status {rc}; inspect its error dialog before retrying.')
        return rc
    if not _app_authorization_result(): return 2
    return status()


def install():
    if ready():
        print('Android is already READY. Use `deckctl android repair` or deliberate `deckctl android reinstall`.')
        return 0
    if IMAGE.is_file():
        return retry()
    return _run()


def repair():
    if not IMAGE.is_file():
        print('No Android image exists; switching to fresh install.')
        return _run()
    return _run('--repair')


def retry():
    if ready():
        return status()
    if IMAGE.is_file() and LAUNCHER.is_file() and os.access(LAUNCHER, os.X_OK):
        return _first_run()
    return repair() if IMAGE.is_file() else install()


def reinstall():
    print('WARNING: deliberate Android recreation. Upstream archives recoverable prior state and asks for confirmation.')
    return _run('--reinstall-android')
