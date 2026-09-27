from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

from . import core

STORE_API = "https://plugins.deckbrew.xyz/plugins"
CDN_TEMPLATE = "https://cdn.tzatzikiweeb.moe/file/steam-deck-homebrew/versions/{hash}.zip"
MAX_ARCHIVE_BYTES = 250 * 1024 * 1024
MAX_UNPACKED_BYTES = 750 * 1024 * 1024
MAX_FILE_BYTES = 250 * 1024 * 1024
RECEIPTS = core.CONFIG_HOME / "decky-install-receipts.json"
BACKUP_ROOT = Path.home() / ".local/share/deckctl/decky-backups"
PLUGIN_ROOT = Path.home() / "homebrew/plugins"


class InstallError(RuntimeError):
    pass


def _current_user_group():
    """Return the invoking user's uid/gid names for narrow permission repairs."""
    import getpass
    import grp
    import pwd

    uid = os.getuid()
    pw = pwd.getpwuid(uid)
    try:
        group = grp.getgrgid(pw.pw_gid).gr_name
    except KeyError:
        group = str(pw.pw_gid)
    return pw.pw_name or getpass.getuser(), group


def _sudo_run(cmd, *, reason: str):
    """Run one narrowly-scoped privileged command, prompting through sudo when required."""
    print(f"\nAdministrator permission required: {reason}")
    print("SteamOS will ask for your sudo password if it is not already cached.")
    try:
        from . import privilege
        result = subprocess.run(privilege.command(cmd), env=privilege.environment(), check=False)
    except FileNotFoundError as exc:
        raise InstallError("sudo is not available; cannot repair Decky plugin permissions") from exc
    if result.returncode != 0:
        raise InstallError(f"Privileged operation failed (exit {result.returncode}): {' '.join(cmd)}")


def _ensure_plugin_root_writable():
    """Ensure only Decky's plugin directory is user-writable; never elevate all of deckctl."""
    user, group = _current_user_group()
    try:
        PLUGIN_ROOT.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Decky's supported installer normally creates this path as the Deck user.
        # Repair only this directory; do not recursively chown ~/homebrew or services.
        _sudo_run(
            ["install", "-d", "-m", "0755", "-o", user, "-g", group, str(PLUGIN_ROOT)],
            reason=f"Decky plugin directory {PLUGIN_ROOT} is not writable",
        )

    if not os.access(PLUGIN_ROOT, os.W_OK | os.X_OK):
        _sudo_run(
            ["chown", f"{user}:{group}", str(PLUGIN_ROOT)],
            reason=f"Decky plugin directory {PLUGIN_ROOT} is owned by another user",
        )
        _sudo_run(
            ["chmod", "u+rwx", str(PLUGIN_ROOT)],
            reason=f"Decky plugin directory {PLUGIN_ROOT} needs user write permission",
        )

    if not os.access(PLUGIN_ROOT, os.W_OK | os.X_OK):
        raise InstallError(f"Decky plugin directory is still not writable after repair: {PLUGIN_ROOT}")


def _fetch_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "deckctl/" + (core.ROOT / "VERSION").read_text().strip()})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read(20 * 1024 * 1024 + 1)
    if len(data) > 20 * 1024 * 1024:
        raise InstallError("Decky Store response was unexpectedly large")
    return json.loads(data.decode("utf-8"))


def _store_catalog():
    data = _fetch_json(STORE_API)
    if isinstance(data, dict):
        # Tolerate future wrappers such as {"plugins": [...]}.
        for key in ("plugins", "data", "results"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
    if not isinstance(data, list):
        raise InstallError("Decky Store returned an unexpected catalog shape")
    return data


def _find_store_plugin(catalog, name: str):
    needle = name.casefold().strip()
    matches = [p for p in catalog if str(p.get("name", "")).casefold().strip() == needle]
    if not matches:
        return None
    visible = [p for p in matches if p.get("visible", True)]
    return (visible or matches)[0]


def _latest_version(plugin):
    versions = plugin.get("versions") or []
    if not versions:
        return None
    # Store currently publishes newest first. If timestamps exist, use them.
    if any(v.get("created") for v in versions):
        versions = sorted(versions, key=lambda v: v.get("created") or "", reverse=True)
    return versions[0]


def _download(url: str, dest: Path):
    req = urllib.request.Request(url, headers={"User-Agent": "deckctl/" + (core.ROOT / "VERSION").read_text().strip()})
    with urllib.request.urlopen(req, timeout=90) as r, dest.open("wb") as f:
        total = 0
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_ARCHIVE_BYTES:
                raise InstallError("Plugin archive exceeds safety size limit")
            f.write(chunk)
    if not zipfile.is_zipfile(dest):
        raise InstallError("Downloaded artifact is not a valid ZIP archive")


def _zip_mode(info: zipfile.ZipInfo) -> int:
    return (info.external_attr >> 16) & 0o7777


def _validate_zip(path: Path, expected_name: str):
    total = 0
    top_levels = set()
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        if not infos:
            raise InstallError("Plugin ZIP is empty")
        for info in infos:
            p = PurePosixPath(info.filename)
            if p.is_absolute() or ".." in p.parts:
                raise InstallError(f"Unsafe path in plugin ZIP: {info.filename}")
            if not p.parts:
                continue
            top_levels.add(p.parts[0])
            if info.file_size > MAX_FILE_BYTES:
                raise InstallError(f"Plugin file exceeds safety size limit: {info.filename}")
            total += info.file_size
            if total > MAX_UNPACKED_BYTES:
                raise InstallError("Plugin archive expands beyond safety size limit")
            mode = (info.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                raise InstallError(f"Symlinks are not allowed in automated Decky installs: {info.filename}")
        if len(top_levels) != 1:
            raise InstallError("Decky plugin ZIP must contain exactly one top-level plugin directory")
        top = next(iter(top_levels))
        required = [f"{top}/plugin.json", f"{top}/package.json", f"{top}/dist/index.js"]
        names = set(z.namelist())
        missing = [x for x in required if x not in names]
        if missing:
            raise InstallError("Plugin ZIP missing required Decky files: " + ", ".join(missing))
        try:
            meta = json.loads(z.read(f"{top}/plugin.json").decode("utf-8"))
        except Exception as exc:
            raise InstallError(f"Could not parse plugin.json: {exc}") from exc
        archive_name = str(meta.get("name", "")).strip()
        if archive_name.casefold() != expected_name.casefold():
            raise InstallError(f"Plugin identity mismatch: expected {expected_name!r}, archive says {archive_name!r}")
        return top, meta


def _extract_plugin(zip_path: Path, top: str, dest: Path):
    staging = dest.parent / f".{dest.name}.deckctl-staging-{os.getpid()}"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(zip_path) as z:
        prefix = top.rstrip("/") + "/"
        for info in z.infolist():
            if not info.filename.startswith(prefix):
                continue
            rel = info.filename[len(prefix):]
            if not rel:
                continue
            out = staging / rel
            if info.is_dir():
                out.mkdir(parents=True, exist_ok=True)
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, out.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            mode = _zip_mode(info)
            if mode:
                out.chmod(mode)
    return staging


def _load_receipts():
    try:
        return json.loads(RECEIPTS.read_text()) if RECEIPTS.exists() else {}
    except Exception:
        return {}


def _save_receipts(data):
    RECEIPTS.parent.mkdir(parents=True, exist_ok=True)
    tmp = RECEIPTS.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    tmp.replace(RECEIPTS)


def _restart_decky():
    from . import user_session
    if user_session.nested_desktop():
        print(user_session.NESTED_DESKTOP_NOTICE)
        return False
    # The stable Decky installer normally creates a system service. Try that first.
    from . import privilege
    attempts = [
        privilege.command(["systemctl", "restart", "plugin_loader"]),
        ["systemctl", "--user", "restart", "plugin_loader"],
    ]
    for cmd in attempts:
        try:
            r = subprocess.run(cmd, env=privilege.environment(), check=False)
            if r.returncode == 0:
                return True
        except FileNotFoundError:
            pass
    return False


def _selected_items():
    selected = core._decky_selected_folders()
    item_map = core._decky_item_map()
    out = []
    for folder in sorted(selected):
        item = item_map.get(folder)
        if item:
            out.append(item)
    return out


def install_selected(*, reinstall: bool = False, dry_run: bool = False, assume_yes: bool = False, only=None) -> int:
    if not core._decky_loader_present():
        print("Decky Loader is not installed. Complete the Decky Loader step first.")
        return 2

    selected = _selected_items()
    if only is not None:
        if only not in {p['folder'] for p in selected}: raise ValueError('Plugin is not selected')
        selected = [p for p in selected if p['folder'] == only]
    installed = core._decky_installed_plugins()
    todo = [p for p in selected if reinstall or p["folder"] not in installed or not installed[p["folder"]].get("valid", False)]
    if not todo:
        if not dry_run: core._decky_upgrade_selection()
        print("All selected Decky plugins are already installed.")
        return 0

    print("DECKY AUTOMATED INSTALL")
    print("Source: Decky's official Plugin Store catalog/artifact CDN")
    print("Selected missing plugins:")
    for p in todo:
        print(f"  - {p['name']}")
    print("\nSafety: packages are identity/structure validated and installed atomically.")
    print("If a package cannot be safely resolved, it is left MISSING for guided Store install.")
    if dry_run:
        return 0
    from . import user_session
    if user_session.nested_desktop():
        print(user_session.NESTED_DESKTOP_NOTICE)
        return 2
    if not assume_yes:
        answer = input("\nInstall these plugins now? [Y/n] ").strip().lower()
        if answer.startswith("n"):
            return 0

    core._decky_upgrade_selection()
    try:
        catalog = _store_catalog()
    except Exception as exc:
        print(f"Could not load Decky Store catalog: {exc}")
        print("No plugins were changed. Use Decky Plugin Store as fallback.")
        return 3

    try:
        _ensure_plugin_root_writable()
    except InstallError as exc:
        print(f"Could not prepare Decky plugin directory: {exc}")
        return 5
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    receipts = _load_receipts()
    failures = []
    changed = []

    with tempfile.TemporaryDirectory(prefix="deckctl-decky-") as td:
        td = Path(td)
        for item in todo:
            name = item["name"]
            folder = item["folder"]
            store = _find_store_plugin(catalog, name)
            if not store:
                failures.append((name, "not found in Decky Store catalog"))
                continue
            ver = _latest_version(store)
            locator = (ver or {}).get("hash")
            version = (ver or {}).get("name")
            if not locator:
                failures.append((name, "Decky Store has no downloadable version"))
                continue
            from . import compatibility
            compatibility_row = compatibility.resolve('plugin:'+folder, str(version or 'unknown'), compatibility.system(), compatibility.database())
            if compatibility_row['status'] == 'UNSUPPORTED':
                failures.append((name, 'Reviewed compatibility record marks this version unsupported'))
                continue
            if compatibility_row['status'] == 'UNKNOWN':
                print(f"{name}: UNKNOWN compatibility; explicitly selected Store package, actual Game Mode loading remains unverified.")
            url = CDN_TEMPLATE.format(hash=locator)
            archive = td / f"{folder}.zip"
            print(f"\n{name}: resolving {version or 'latest'}")
            try:
                _download(url, archive)
                archive_sha = hashlib.sha256(archive.read_bytes()).hexdigest()
                top, meta = _validate_zip(archive, name)
                target = PLUGIN_ROOT / folder
                staging = _extract_plugin(archive, top, target)
                backup = None
                if target.exists():
                    backup = BACKUP_ROOT / f"{folder}-{time.strftime('%Y%m%d-%H%M%S')}"
                    target.rename(backup)
                try:
                    staging.rename(target)
                except Exception:
                    if backup and backup.exists() and not target.exists():
                        backup.rename(target)
                    raise
                receipts[folder] = {
                    "name": name,
                    "store_version": version,
                    "store_locator": locator,
                    "source": url,
                    "archive_sha256": archive_sha,
                    "installed_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "plugin_author": meta.get("author"),
                }
                changed.append(name)
                print(f"  INSTALLED {name} ({version or 'unknown version'})")
            except (urllib.error.URLError, InstallError, zipfile.BadZipFile, OSError, ValueError) as exc:
                failures.append((name, str(exc)))
                print(f"  FALLBACK REQUIRED: {exc}")

    _save_receipts(receipts)
    if changed:
        print("\nRestarting Decky Loader once...")
        if not _restart_decky():
            print("Could not restart Decky automatically. Return to Game Mode/reboot, then run `dplugins`.")

    # Post-install audit from filesystem.
    installed_after = core._decky_installed_plugins()
    unresolved = [p["name"] for p in selected if p["folder"] not in installed_after or not installed_after[p["folder"]].get("valid", False)]
    print("\nRESULT")
    print(f"Installed this run: {len(changed)}")
    if unresolved:
        print("Still missing / guided fallback:")
        for name in unresolved:
            print(f"  - {name}")
    else:
        print("All selected Decky plugins are present.")

    if failures:
        print("\nAutomatic-install notes:")
        for name, reason in failures:
            print(f"  {name}: {reason}")
        print("Use Decky's built-in Plugin Store for the unresolved entries.")

    return 0 if not unresolved else 4


def receipts():
    data = _load_receipts()
    if not data:
        print("No deckctl automated Decky install receipts found.")
        return
    print(json.dumps(data, indent=2, sort_keys=True))
