from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

from . import core, controller, css_stack, decky_installer, lifecycle, terminal

CSS_DIR = Path.home() / "homebrew/themes"
CSS_SNAPSHOTS = core.CONFIG_HOME / "css-profiles"
UI_SAFE_STATE = core.STATE / "ui-safe.json"
CONTROL_BASE = Path.home() / ".local/share/steamdeck-workstation"
RELEASES_DIR = CONTROL_BASE / "releases"
CURRENT_LINK = CONTROL_BASE / "current"
UPDATE_HISTORY = core.STATE / "update-history.json"
PROFILE_EXPORT_DIR = Path.home() / "DeckExports"

SENSITIVE_KEY_RE = re.compile(r"(password|passwd|secret|token|cookie|credential|private.?key|auth|session|api.?key)", re.I)
NETWORK_PRIVATE_KEY_RE = re.compile(r"(target|mac|relay_ssh)", re.I)


def _stamp():
    return time.strftime("%Y%m%d-%H%M%S")


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _hash_tree(path: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(x for x in path.rglob("*") if x.is_file()):
        h.update(str(p.relative_to(path)).encode())
        h.update(b"\0")
        h.update(_hash_file(p).encode())
        h.update(b"\0")
    return h.hexdigest()


def _profile_dirs(root: Path):
    if not root.exists():
        return []
    return sorted([p for p in root.iterdir() if p.is_dir() and p.name.endswith(".profile")], key=lambda p: p.name.casefold())


def css_profiles_list():
    live = _profile_dirs(CSS_DIR)
    captured = _profile_dirs(CSS_SNAPSHOTS)
    print("CSS LOADER PROFILES")
    print(f"Live:     {CSS_DIR}")
    for p in live:
        print(f"  LIVE      {p.name}")
    if not live:
        print("  LIVE      none")
    print(f"Captured: {CSS_SNAPSHOTS}")
    for p in captured:
        print(f"  CAPTURED  {p.name}")
    if not captured:
        print("  CAPTURED  none")
    return 0


def _resolve_profile(root: Path, name: str):
    if Path(name).name != name or name in (".", "..") or "\\" in name:
        raise ValueError("Profile name must be a single directory name")
    wanted = name if name.endswith(".profile") else f"{name}.profile"
    direct = root / wanted
    if direct.is_dir():
        return direct
    matches = [p for p in _profile_dirs(root) if p.name.casefold() == wanted.casefold()]
    return matches[0] if matches else None


def css_profile_capture(name: str | None = None):
    CSS_SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    live = [_resolve_profile(CSS_DIR, name)] if name else _profile_dirs(CSS_DIR)
    live = [p for p in live if p]
    if not live:
        print("No CSS Loader profile found to capture.")
        print("In Game Mode: QAM -> Decky -> CSS Loader -> Selected Profile -> New Profile")
        return 2
    manifest = {"captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "profiles": {}}
    for src in live:
        dest = CSS_SNAPSHOTS / src.name
        tmp = dest.with_name(dest.name + ".new")
        if tmp.exists():
            shutil.rmtree(tmp)
        shutil.copytree(src, tmp)
        if dest.exists():
            shutil.rmtree(dest)
        tmp.rename(dest)
        manifest["profiles"][src.name] = {"sha256_tree": _hash_tree(dest)}
        print(f"Captured {src.name} -> {dest}")
    core.save_json(CSS_SNAPSHOTS / "capture-manifest.json", manifest)
    return 0


def css_profile_restore(name: str | None = None):
    captured = [_resolve_profile(CSS_SNAPSHOTS, name)] if name else _profile_dirs(CSS_SNAPSHOTS)
    captured = [p for p in captured if p]
    if not captured:
        print("No captured CSS Loader profiles found. Run: deckctl decky css capture")
        return 2
    CSS_DIR.mkdir(parents=True, exist_ok=True)
    rollback = core.STATE / "css-profile-restore" / _stamp()
    for src in captured:
        dest = CSS_DIR / src.name
        if dest.exists():
            rollback.mkdir(parents=True, exist_ok=True)
            shutil.copytree(dest, rollback / dest.name)
        tmp = dest.with_name(dest.name + ".restore-new")
        if tmp.exists():
            shutil.rmtree(tmp)
        shutil.copytree(src, tmp)
        if dest.exists():
            shutil.rmtree(dest)
        tmp.rename(dest)
        print(f"Restored {src.name} -> {dest}")
    if rollback.exists():
        print(f"Previous live copies saved under: {rollback}")
    print("Game Mode -> CSS Loader -> Refresh, then select the restored profile.")
    return 0


def _installed_css_by_name():
    # Use css_stack's exact-name inventory logic so the safe-mode manifest follows the same names as dcss.
    return css_stack._installed_themes()  # intentionally shared internal helper


def ui_safe(minimal: bool = False):
    if UI_SAFE_STATE.exists():
        print("UI safe mode is already active. Restore first with: deckctl ui restore")
        return 2
    stack = css_stack._stack()
    installed = _installed_css_by_name()
    names = []
    if minimal:
        names.extend(x["name"] for sec in ("required", "recommended", "optional") for x in stack.get(sec, []))
        names.append("Bubble Gum Rave")
    else:
        names.extend(x["name"] for x in stack.get("optional", []))
    roots = []
    for name in names:
        found = css_stack._find(installed, name)
        if found and found["path"].is_dir() and found["path"] not in roots:
            roots.append(found["path"])
    # Hard/minimal mode also removes profile directories, guaranteeing no profile can re-enable missing layers.
    if minimal:
        roots.extend(p for p in _profile_dirs(CSS_DIR) if p not in roots)
    if not roots:
        print("No matching CSS layers are currently installed; nothing to quarantine.")
        return 0
    quarantine = core.STATE / "ui-safe" / _stamp()
    quarantine.mkdir(parents=True, exist_ok=True)
    moved = []
    for src in roots:
        dest = quarantine / src.name
        shutil.move(str(src), str(dest))
        moved.append({"name": src.name, "from": str(src), "to": str(dest)})
        print(f"Disabled {src.name}")
    core.save_json(UI_SAFE_STATE, {"created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "minimal": minimal, "quarantine": str(quarantine), "moved": moved})
    print("UI safe mode enabled. Return to Game Mode and refresh CSS Loader / restart Steam if needed.")
    print("Restore with: deckctl ui restore")
    return 0


def ui_restore():
    state = core.load_json(UI_SAFE_STATE, None)
    if not state:
        print("UI safe mode is not active.")
        return 0
    conflicts = 0
    for item in state.get("moved", []):
        src = Path(item["to"])
        dest = Path(item["from"])
        if not src.exists():
            continue
        if dest.exists():
            print(f"CONFLICT: {dest} already exists; leaving quarantined copy at {src}")
            conflicts += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        print(f"Restored {dest.name}")
    if conflicts == 0:
        UI_SAFE_STATE.unlink(missing_ok=True)
    print("Return to Game Mode and refresh CSS Loader / restart Steam if needed.")
    return 1 if conflicts else 0


def _sanitize(value, support_bundle=False):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if SENSITIVE_KEY_RE.search(str(k)) or (support_bundle and NETWORK_PRIVATE_KEY_RE.search(str(k))):
                out[k] = "<redacted>"
            else:
                out[k] = _sanitize(v, support_bundle=support_bundle)
        return out
    if isinstance(value, list):
        return [_sanitize(v, support_bundle=support_bundle) for v in value]
    if isinstance(value, str):
        # Avoid accidentally shipping bearer/basic credentials embedded in strings.
        if re.search(r"(?i)((?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}|password=|token=|secret=|-----BEGIN .*PRIVATE KEY-----)", value):
            return "<redacted>"
    return value


# Portable profiles are data, never executable shell or arbitrary home content.
PROFILE_JSON = {'settings.json', 'games.json', 'hosts.json', 'decky-selection.json',
                'css-stack-receipt.json', 'decky-install-receipts.json'}

def _portable_file(relative: Path):
    parts = relative.parts
    if not parts or any(SENSITIVE_KEY_RE.search(part) for part in parts): return False
    if len(parts) == 1: return relative.name in PROFILE_JSON
    if parts[0] == 'controller-layouts': return len(parts) == 2 and relative.suffix in ('.vdf', '.json')
    if parts[0] == 'terminal': return len(parts) == 2 and relative.suffix == '.json'
    if parts[0] == 'css-profiles':
        if len(parts) == 2: return parts[1] == 'capture-manifest.json'
        return parts[1].endswith('.profile') and relative.suffix.lower() in ('.json', '.png', '.jpg', '.jpeg', '.webp')
    return False

def _portable_bytes(path: Path):
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError(f'Profile file too large: {path.name}')
    raw = path.read_bytes()
    ext = path.suffix.lower()
    if ext == '.json':
        value = json.loads(raw)
        if not isinstance(value, (dict, list)): raise ValueError('Configuration must be an object or array')
        return (json.dumps(_sanitize(value), indent=2) + '\n').encode()
    if ext == '.vdf':
        text = raw.decode('utf-8')
        if '\x00' in text or SENSITIVE_KEY_RE.search(text) or '-----BEGIN' in text:
            raise ValueError('Unsafe controller layout content')
    elif ext == '.png' and not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Invalid PNG asset')
    elif ext in ('.jpg', '.jpeg') and not raw.startswith(b'\xff\xd8\xff'):
        raise ValueError('Invalid JPEG asset')
    elif ext == '.webp' and not (raw.startswith(b'RIFF') and raw[8:12] == b'WEBP'):
        raise ValueError('Invalid WebP asset')
    return raw

def _no_link_path(path: Path, root: Path):
    if root.is_symlink(): raise ValueError('Configuration root must not be a symlink')
    for part in (path, *path.parents):
        if part.is_symlink(): raise ValueError(f'Symlink not allowed in profile path: {part}')
        if part == root: break

def profile_export(out: str | None = None):
    # Capture current CSS profiles first so the exported desired state includes their exact settings/custom images.
    if _profile_dirs(CSS_DIR):
        css_profile_capture()
    PROFILE_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    dest = Path(os.path.expanduser(out)) if out else PROFILE_EXPORT_DIR / f"deck-profile-{_stamp()}.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": 1,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "deckctl_version": (core.ROOT / "VERSION").read_text().strip(),
        "note": "Portable desired-state bundle. Browser/Keeper credentials, cookies, ROMs, BIOS and private keys are intentionally excluded.",
    }
    with tempfile.TemporaryDirectory(prefix="deckctl-profile-export-") as td:
        root = Path(td)
        (root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        cfgout = root / "deckctl-config"
        cfgout.mkdir()
        for p in sorted(core.CONFIG_HOME.rglob('*')) if core.CONFIG_HOME.exists() else []:
            relative = p.relative_to(core.CONFIG_HOME)
            if not p.is_file() or not _portable_file(relative): continue
            try:
                _no_link_path(p, core.CONFIG_HOME)
                data = _portable_bytes(p)
            except (ValueError, OSError) as exc:
                print(f'Excluded {relative}: {exc}')
                continue
            target = cfgout / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for p in root.rglob("*"):
                if p.is_file():
                    z.write(p, p.relative_to(root))
    print(dest)
    print("Contains desired state and captured CSS/controller configuration; no browser/Keeper credential stores are included.")
    return dest


def _safe_zip_extract(zf: zipfile.ZipFile, dest: Path):
    entries = zf.infolist()
    if len(entries) > 10000 or sum(i.file_size for i in entries) > 256 * 1024 * 1024:
        raise RuntimeError("Profile archive exceeds extraction limits")
    seen = set()
    for info in entries:
        name = info.filename
        canonical = str(Path(name))
        if canonical in seen or "\\" in name:
            raise RuntimeError(f"duplicate or nonportable archive path: {name}")
        seen.add(canonical)
        if name.startswith(("/", "\\")) or ".." in Path(name).parts:
            raise RuntimeError(f"unsafe archive path: {name}")
        # Reject symlink-like unix entries.
        mode = (info.external_attr >> 16) & 0o170000
        if mode not in (0, 0o100000, 0o040000):
            raise RuntimeError(f"symlink not allowed: {name}")
    zf.extractall(dest)


def profile_import(archive: str):
    arc = Path(os.path.expanduser(archive)).resolve()
    if not arc.exists():
        raise SystemExit(f"Profile archive not found: {arc}")
    with tempfile.TemporaryDirectory(prefix="deckctl-profile-import-") as td:
        tmp = Path(td)
        with zipfile.ZipFile(arc) as z:
            _safe_zip_extract(z, tmp)
        manifest = json.loads((tmp / "manifest.json").read_text())
        if manifest.get("format") != 1:
            raise SystemExit("Unsupported profile bundle format")
        src = tmp / "deckctl-config"
        if not src.is_dir():
            raise SystemExit("Profile bundle is missing deckctl-config")
        # Validate every input and destination before modifying any live file.
        planned = []
        for p in sorted(src.rglob('*')):
            if p.is_dir(): continue
            relative = p.relative_to(src)
            if not _portable_file(relative):
                raise ValueError(f'Unsupported profile payload: {relative}')
            dest = core.CONFIG_HOME / relative
            _no_link_path(dest, core.CONFIG_HOME)
            if dest.exists() and not dest.is_file(): raise ValueError(f'Non-file destination: {relative}')
            planned.append((relative, dest, _portable_bytes(p)))
        backup = core.STATE / "profile-import-rollback" / f'{_stamp()}-{time.time_ns()}'
        backup.mkdir(parents=True, exist_ok=True)
        written = []
        try:
            for relative, dest, data in planned:
                previous = backup / relative
                if dest.exists():
                    previous.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(dest, previous)
                written.append((dest, previous))
                dest.parent.mkdir(parents=True, exist_ok=True)
                fd, name = tempfile.mkstemp(prefix='.profile-', dir=dest.parent)
                tmpfile = Path(name)
                try:
                    with os.fdopen(fd, 'wb') as stream: stream.write(data)
                    tmpfile.replace(dest)
                finally:
                    tmpfile.unlink(missing_ok=True)
        except Exception:
            for dest, previous in reversed(written):
                if previous.exists(): shutil.copy2(previous, dest)
                else: dest.unlink(missing_ok=True)
            raise
        print(f"Imported desired state from {arc}")
        print(f"Previous config rollback copy: {backup}")
        print("Run: deckctl decky css restore && deckctl controller install-templates && deckctl terminal apply --config-only && deckctl verify")
    return 0


def _github_release(repo: str, channel: str):
    headers = {"User-Agent": "deckctl-update"}
    url = f"https://api.github.com/repos/{repo}/releases/latest" if channel == "stable" else f"https://api.github.com/repos/{repo}/releases"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    if channel == "stable":
        return data
    releases = data if isinstance(data, list) else []
    if channel == "beta":
        for rel in releases:
            if rel.get("prerelease") and not rel.get("draft"):
                return rel
    if channel == "dev":
        for rel in releases:
            if not rel.get("draft"):
                return rel
    return None


def update_check():
    cfg = core.load_json(core.ROOT / "config/default.json", {})
    repo = cfg.get("release", {}).get("github_repo")
    current = (core.ROOT / "VERSION").read_text().strip()
    channel = core.settings().get("channel", cfg.get("channel", "stable"))
    print(f"Installed version: {current}")
    print(f"Channel: {channel}")
    if not repo:
        print("GitHub release source is not configured yet. Local archive updates still work with `deckctl update apply --archive FILE`.")
        return 0
    try:
        rel = _github_release(repo, channel)
    except Exception as exc:
        print(f"Unable to query GitHub releases: {exc}")
        return 1
    if not rel:
        print(f"No {channel} release found")
        return 1
    print(f"Latest release: {rel.get('tag_name')}")
    print(rel.get("html_url", ""))
    return 0


def _download_release_archive():
    cfg = core.load_json(core.ROOT / "config/default.json", {})
    repo = cfg.get("release", {}).get("github_repo")
    if not repo:
        raise SystemExit("No GitHub release source configured. Use: deckctl update apply --archive FILE")
    channel = core.settings().get("channel", cfg.get("channel", "stable"))
    rel = _github_release(repo, channel)
    if not rel:
        raise SystemExit(f"No {channel} release found")
    assets = rel.get("assets", [])
    tar_asset = next((a for a in assets if a.get("name", "").startswith("steamdeck-workstation-") and a.get("name", "").endswith(".tar.gz")), None)
    sums_asset = next((a for a in assets if "SHA256SUMS" in a.get("name", "").upper()), None)
    if not tar_asset or not sums_asset:
        raise SystemExit("Release is missing the tar.gz or SHA256SUMS asset; refusing an unverified automatic update")
    dl = core.STATE / "downloads"; dl.mkdir(parents=True, exist_ok=True)
    tar_path = dl / tar_asset["name"]
    sums_path = dl / sums_asset["name"]
    headers = {"User-Agent": "deckctl-update"}
    for asset, dest in ((tar_asset, tar_path), (sums_asset, sums_path)):
        req = urllib.request.Request(asset["browser_download_url"], headers=headers)
        with urllib.request.urlopen(req, timeout=60) as r, dest.open("wb") as f:
            shutil.copyfileobj(r, f)
    expected = None
    for line in sums_path.read_text().splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == tar_path.name:
            expected = parts[0].lower(); break
    if not expected:
        raise SystemExit("Could not find release tarball in SHA256SUMS")
    actual = _hash_file(tar_path)
    if actual != expected:
        raise SystemExit(f"SHA256 mismatch for {tar_path.name}")
    print(f"Verified {tar_path.name} sha256={actual}")
    return tar_path


def _extract_release(archive: Path, dest: Path):
    with tarfile.open(archive, "r:gz") as tf:
        members = tf.getmembers()
        if len(members) > 20000 or sum(m.size for m in members) > 512 * 1024 * 1024:
            raise RuntimeError("Release archive exceeds extraction limits")
        seen = set()
        for m in members:
            name = m.name
            canonical = str(Path(name))
            if canonical in seen or "\\" in name or not (m.isfile() or m.isdir()):
                raise RuntimeError(f"unsafe or duplicate release archive entry: {name}")
            seen.add(canonical)
            if name.startswith(("/", "\\")) or ".." in Path(name).parts or m.issym() or m.islnk():
                raise RuntimeError(f"unsafe release archive entry: {name}")
        tf.extractall(dest, filter="data")
    candidates = [p for p in dest.iterdir() if p.is_dir() and (p / "VERSION").exists() and (p / "bin/deckctl").exists()]
    if len(candidates) != 1:
        raise RuntimeError("release archive must contain exactly one deckctl repository root")
    return candidates[0]


def _history_append(frm: str | None, to: str):
    h = core.load_json(UPDATE_HISTORY, {"events": []}) or {"events": []}
    h.setdefault("events", []).append({"at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "from": frm, "to": to})
    h["events"] = h["events"][-25:]
    core.save_json(UPDATE_HISTORY, h)


def _cleanup_update_download(archive, expected_hash):
    """Delete only the unchanged automatic download, never a supplied archive."""
    directory = core.STATE / 'downloads'
    if archive.parent != directory or any(p.is_symlink() for p in (archive, *archive.parents)):
        return
    if archive.is_file() and _hash_file(archive) == expected_hash:
        archive.unlink()
        print(f'Removed verified updater download: {archive.name}')


def update_apply(archive: str | None = None):
    arc = Path(os.path.expanduser(archive)).resolve() if archive else _download_release_archive()
    if not arc.exists():
        raise SystemExit(f"Update archive not found: {arc}")
    download_hash = _hash_file(arc) if archive is None else None
    previous = str(CURRENT_LINK.resolve()) if CURRENT_LINK.exists() else None
    with tempfile.TemporaryDirectory(prefix="deckctl-update-") as td:
        root = _extract_release(arc, Path(td))
        from . import upgrade_plan
        upgrade_plan.show(root)
        r = subprocess.run([str(root / "bin/deckctl"), "repo", "validate"], cwd=root)
        if r.returncode:
            print("New release validation failed; current version left unchanged.")
            return 1
        install = root / "tools/install-control-plane"
        r = subprocess.run([str(install), str(root)], text=True, capture_output=True)
        if r.returncode:
            print(r.stdout); print(r.stderr)
            print("Control-plane install failed; current version left unchanged where possible.")
            return r.returncode
        new_root = Path(r.stdout.strip().splitlines()[-1]).resolve()
        _history_append(previous, str(new_root))
        print(f"Updated deckctl control plane -> {new_root}")
        print("Run: deckctl verify && deckctl health")
        if download_hash and CURRENT_LINK.resolve() == new_root and (new_root / 'VERSION').is_file():
            try:
                _cleanup_update_download(arc, download_hash)
            except OSError as exc:
                print(f'Update succeeded; download cleanup deferred: {exc}')
    return 0


def update_rollback():
    if not RELEASES_DIR.exists():
        print("No persistent release directory found.")
        return 2
    current = CURRENT_LINK.resolve() if CURRENT_LINK.exists() else None
    hist = core.load_json(UPDATE_HISTORY, {"events": []}) or {"events": []}
    candidate = None
    for event in reversed(hist.get("events", [])):
        value = event.get("from")
        if not value: continue
        p = Path(value).resolve()
        if p.parent == RELEASES_DIR.resolve() and (p / "VERSION").is_file() and (p / "tools/install-control-plane").is_file() and p != current:
            candidate = p; break
    if candidate is None:
        releases = sorted([p for p in RELEASES_DIR.iterdir() if p.is_dir() and not p.is_symlink() and (p / "VERSION").is_file() and (p / "tools/install-control-plane").is_file() and p != current], key=lambda p: p.stat().st_mtime, reverse=True)
        candidate = releases[0] if releases else None
    if not candidate:
        print("No previous release is available to roll back to.")
        return 2
    r = subprocess.run([str(candidate / "tools/install-control-plane"), str(candidate)], text=True, capture_output=True)
    if r.returncode:
        print(r.stdout); print(r.stderr); return r.returncode
    new_root = Path(r.stdout.strip().splitlines()[-1]).resolve()
    _history_append(str(current) if current else None, str(new_root))
    print(f"Rolled back deckctl -> {new_root}")
    print("Run: deckctl verify && deckctl health")
    return 0


def _perm_row(path: Path):
    try:
        st = path.stat()
        return {"path": str(path), "exists": True, "mode": oct(st.st_mode & 0o777), "uid": st.st_uid, "gid": st.st_gid, "writable": os.access(path, os.W_OK)}
    except FileNotFoundError:
        return {"path": str(path), "exists": False}


def support_bundle():
    outdir = Path.home() / "DeckSupportBundles"; outdir.mkdir(parents=True, exist_ok=True)
    stamp = _stamp(); out = outdir / f"deck-support-{stamp}.zip"
    with tempfile.TemporaryDirectory(prefix="deckctl-support-") as td:
        root = Path(td)
        inventory = {
            "version": (core.ROOT / "VERSION").read_text().strip(),
            "hardware": core.detect_hardware(),
            "modules": {m: core.module_status(m) for m in core.topo(core.enabled_modules())},
            "storage": core.storage_health(quiet=True),
            "setup": core.setup_state(),
            "permissions": [_perm_row(Path.home()/"homebrew"), _perm_row(Path.home()/"homebrew/plugins"), _perm_row(Path.home()/"homebrew/themes")],
            "css_profiles": [p.name for p in _profile_dirs(CSS_DIR)],
            "css_captured_profiles": [p.name for p in _profile_dirs(CSS_SNAPSHOTS)],
            "ui_safe_mode": bool(UI_SAFE_STATE.exists()),
            "terminal": terminal.status_data(),
        }
        (root / "inventory.json").write_text(json.dumps(_sanitize(inventory, support_bundle=True), indent=2) + "\n")
        # Include only known-safe config summaries, not arbitrary home/browser files.
        cfg = root / "config"; cfg.mkdir()
        for name in ("settings.json", "decky-selection.json"):
            p = core.CONFIG_HOME / name
            if p.exists():
                try: data = _sanitize(json.loads(p.read_text()), support_bundle=True)
                except Exception: continue
                (cfg / name).write_text(json.dumps(data, indent=2) + "\n")
        receipts = core.CONFIG_HOME / "decky-receipts"
        if receipts.exists():
            outrec = cfg / "decky-receipts"; outrec.mkdir()
            for p in receipts.glob("*.json"):
                try: data = _sanitize(json.loads(p.read_text()), support_bundle=True)
                except Exception: continue
                (outrec / p.name).write_text(json.dumps(data, indent=2) + "\n")
        # Package/app versions are helpful and do not contain account data.
        if shutil.which("flatpak"):
            r = subprocess.run(["flatpak", "list", "--app", "--columns=application,version,branch"], text=True, capture_output=True)
            (root / "flatpaks.txt").write_text(r.stdout)
        (root / "README.txt").write_text(
            "Sanitized deckctl support bundle. Review before sharing.\n"
            "Intentionally excluded: browser profiles, Keeper data, cookies, credentials, tokens, ROMs, BIOS/firmware, private keys, save payloads, shell history, and remote-host addresses/MACs.\n"
        )
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for p in root.rglob("*"):
                if p.is_file(): z.write(p, p.relative_to(root))
    print(out)
    return out


def post_update():
    print("POST-STEAMOS UPDATE RECOVERY")
    print(f"deckctl {(core.ROOT/'VERSION').read_text().strip()}")
    # Always restage vendor installers/assets from the active release. This is safe and user-space only.
    result = core.run_action("decky", "install")
    failures = ["decky staging"] if result is not None and result.returncode else []
    decky_present = core._decky_loader_present()
    print(f"Decky Loader       {'FOUND' if decky_present else 'MISSING / INTERACTIVE REINSTALL REQUIRED'}")
    if not decky_present:
        failures.append("Decky Loader missing")
        stage = Path.home()/"Desktop/Deck-Setup-Staged/decky_installer.desktop"
        print(f"Run the staged official Decky installer in Desktop Mode: {stage}")
    else:
        rc = decky_installer.install_selected(assume_yes=True)
        if rc: failures.append("Decky plugins")
        print(f"Decky plugins      {'RECONCILED' if rc == 0 else 'REVIEW REQUIRED'}")
        if core._decky_cssloader_desired() and (Path.home()/"homebrew/plugins/SDH-CssLoader").exists():
            if core.decky_theme_install(): failures.append("CSS components")
    if _profile_dirs(CSS_SNAPSHOTS) and not _profile_dirs(CSS_DIR):
        print("CSS Loader profiles disappeared; restoring captured copies...")
        if css_profile_restore(): failures.append("CSS profiles")
    try:
        if controller.install_templates(): failures.append("controller templates")
    except Exception as exc:
        failures.append("controller templates")
        print(f"Controller templates: WARN ({exc})")
    try:
        rc = terminal.apply(config_only=True)
        if rc: failures.append("terminal")
        print("Terminal profile     " + ("REVIEW REQUIRED" if rc else "REASSERTED"))
    except Exception as exc:
        failures.append("terminal")
        print(f"Terminal profile: WARN ({exc})")
    os_state = {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "hardware": core.detect_hardware()}
    core.save_json(core.STATE / "post-update.json", os_state)
    print("\nFinal health check:")
    lifecycle.health(False)
    print("\nIf Game Mode styling is broken: deckctl ui safe")
    if failures: print("Recovery needs attention: " + ", ".join(failures))
    return 1 if failures else 0
