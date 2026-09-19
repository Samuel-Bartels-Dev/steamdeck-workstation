"""Remove only verified, unchanged, project-staged one-shot installers."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from . import core, desktop

FILES = {
    'emudeck': ('EmuDeck.desktop', 'README-EMUDECK.txt'),
    'decky': ('decky_installer.desktop',),
    'android': ('Waydroid-Android.desktop',),
    'tailscale': ('Install-Tailscale.desktop',),
}
# Exact official legacy downloader, not the installed EmuDeck management app.
LEGACY_EMUDECK = """[Desktop Entry]
Comment[en_US]=
Comment=
Exec=sh -c 'curl -L https://raw.githubusercontent.com/dragoonDorise/EmuDeck/main/install.sh | bash'
GenericName[en_US]=
GenericName=
MimeType=
Name[en]=Install EmuDeck
Name[es]=Instalar EmuDeck
Name=Install EmuDeck
Path=
StartupNotify=false
Terminal=true
TerminalOptions=
Type=Application
X-DBUS-ServiceName=
X-DBUS-StartupType=
X-KDE-SubstituteUID=false
X-KDE-Username=
"""


def emudeck_ready():
    home = Path.home()
    config = home / '.config/EmuDeck'
    app = home / 'Applications/EmuDeck.AppImage'
    # Vendor completion markers plus the actual manager; an empty Emulation
    # directory or downloaded installer is never completion evidence.
    return app.is_file() and os.access(app, os.X_OK) and not (config / 'install.pid').exists() and all(
        (config / name).is_file() for name in ('.finished', '.ui-finished'))


def _receipt():
    return core.STATE / 'installer-artifacts.json'


def _regular(path):
    # Never follow directory symlinks out of the known staging/Desktop paths.
    return path.is_file() and not any(p.is_symlink() for p in (path, *path.parents))


def _sha(path):
    if not _regular(path) or path.stat().st_size > 1024 * 1024:
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(step):
    """Called only after a module successfully writes its known staging files."""
    if step not in FILES:
        raise ValueError('Unknown installer step')
    receipt = core.load_json(_receipt(), {}) or {}
    stage = Path.home() / 'Desktop/Deck-Setup-Staged'
    for name in FILES[step]:
        digest = _sha(stage / name)
        if digest:
            receipt[f'{step}/{name}'] = digest
    core.save_json(_receipt(), receipt)
    return 0


def verified(step):
    if step == 'emudeck': return emudeck_ready()
    if step == 'decky': return core._decky_loader_present()
    if step == 'android':
        from . import android
        return android.ready()
    if step == 'tailscale':
        # Reuse the guided detector; this removes only the installer launcher,
        # never the installed service or its authentication state.
        return 'tailscale' in core.setup_state().get('completed', []) and next(s for s in core.setup_steps() if s['id'] == 'tailscale')['detect']()
    return False


def cleanup(dry_run=False):
    stage = Path.home() / 'Desktop/Deck-Setup-Staged'
    desk = desktop.desktop_dir()
    receipt = core.load_json(_receipt(), {}) or {}
    failed = False
    for step, names in FILES.items():
        candidates = [(stage / name, name) for name in names]
        candidates += [(desk / names[0], names[0])]
        if step == 'emudeck':
            candidates += [(desk / name, 'EmuDeck.desktop') for name in ('Install EmuDeck.desktop', 'EmuDeck.desktop.download')]
        if not any(path.is_file() for path, _ in candidates): continue
        try:
            if not verified(step):
                print(f'KEEP {step}: installation not verified')
                continue
            for path, name in candidates:
                if not path.exists(): continue
                digest = _sha(path)
                known = receipt.get(f'{step}/{name}')
                legacy = step == 'emudeck' and name == 'EmuDeck.desktop' and digest in {hashlib.sha256(s.encode()).hexdigest() for s in (LEGACY_EMUDECK, LEGACY_EMUDECK.rstrip('\n'))}
                if not digest or not (digest == known or legacy):
                    print(f'KEEP modified/untracked installer: {path}')
                    continue
                print(f'{"WOULD REMOVE" if dry_run else "REMOVE"} verified installer: {path}')
                if not dry_run: path.unlink()
        except (OSError, ValueError, StopIteration) as exc:
            failed = True
            print(f'Installer cleanup deferred for {step}: {exc}')
    if not dry_run and stage.is_dir() and not stage.is_symlink():
        try: stage.rmdir()  # Only when empty; never recursively delete staging.
        except OSError: pass
    return 1 if failed else 0


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['record', 'emudeck-ready'])
    parser.add_argument('step', nargs='?', choices=list(FILES))
    args = parser.parse_args()
    if args.action == 'record':
        if not args.step: parser.error('record requires a step')
        raise SystemExit(record(args.step))
    raise SystemExit(0 if emudeck_ready() else 1)
