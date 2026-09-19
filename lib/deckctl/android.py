from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

HOME = Path.home()
CHECKOUT = HOME / 'steamos-waydroid-bundle'
IMAGE = HOME / 'Android_Waydroid/waydroid.img'
STATE = HOME / '.local/share/waydroid'
LEGACY = HOME / 'waydroid'
SHORTCUT_HELPER = HOME / 'Android_Waydroid/steam-shortcuts.py'
LAUNCHER = HOME / 'Android_Waydroid/Android_Waydroid_Cage.sh'


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
    if not _ensure_checkout():
        return 1
    cmd = [str(CHECKOUT / 'steamos-waydroid-installer.sh')]
    if mode:
        cmd.append(mode)
    print('Launching SteamOS Waydroid installer.')
    print('For a fresh install choose: Android 13 with Google Play.')
    print('The upstream installer may request your sudo password for host integration.')
    print('Steam shortcut creation is detached so Steam cannot keep this setup terminal open.')

    env = os.environ.copy()
    real_add = shutil.which('steamos-add-to-steam')
    if not real_add:
        rc = subprocess.run(cmd, cwd=CHECKOUT, env=env).returncode
    else:
        with tempfile.TemporaryDirectory(prefix='deckctl-waydroid-') as tmp:
            shim_dir = Path(tmp)
            _write_nonblocking_steam_shim(shim_dir, real_add)
            env['PATH'] = f"{shim_dir}:{env.get('PATH', '')}"
            rc = subprocess.run(cmd, cwd=CHECKOUT, env=env).returncode

    if rc != 0:
        return rc
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


def _first_run():
    """Use the vendor launcher that mounts the existing image before opening Android."""
    if not IMAGE.is_file() or not LAUNCHER.is_file() or not os.access(LAUNCHER, os.X_OK):
        print('Android CONFIG_REQUIRED: bundled launcher/image missing; run deckctl android repair.')
        return 2
    if not (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        print('Android CONFIG_REQUIRED: first launch requires Desktop Mode. Run deckctl android retry there.')
        return 2
    print('Opening the installed Android image with its bundled Waydroid launcher.', flush=True)
    print('Complete Android/Google Play sign-in if prompted, then close Android to resume provisioning.', flush=True)
    try:
        rc = subprocess.run([str(LAUNCHER)], cwd=LAUNCHER.parent).returncode
    except OSError as exc:
        print(f'Android launcher failed: {exc}')
        return 2
    if rc != 0:
        print(f'Android launcher exited with status {rc}; inspect its error dialog before retrying.')
        return rc
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
