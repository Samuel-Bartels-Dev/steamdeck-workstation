from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import shlex
import subprocess
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path

from . import core

HOME = Path.home()
BIN_DIR = HOME / ".local/bin"
MAN_DIR = HOME / ".local/share/man"
FONT_DIR = HOME / ".local/share/fonts/deckctl-jetbrainsmono"
KONSOLE_DIR = HOME / ".local/share/konsole"
TERM_CONFIG = core.CONFIG_HOME / "terminal"
SHELL_CONFIG = core.CONFIG_HOME / "shell" / "terminal.sh"
STARSHIP_CONFIG = TERM_CONFIG / "starship.toml"
POSH_CONFIG = TERM_CONFIG / "bubble-gum-rave.omp.json"
PROMPT_ENGINE_FILE = TERM_CONFIG / "prompt-engine"
STATE_FILE = core.STATE / "terminal.json"
RECEIPTS_FILE = core.STATE / "terminal-receipts.json"
BASHRC = HOME / ".bashrc"
KONSOLERC = HOME / ".config/konsolerc"
TMUXRC = HOME / ".tmux.conf"
TMUX_CONFIG = TERM_CONFIG / "tmux.conf"

SHELL_MARKER_START = "# >>> steamdeck-workstation terminal >>>"
SHELL_MARKER_END = "# <<< steamdeck-workstation terminal <<<"
KONSOLE_PROFILE = "Bubble Gum Rave.profile"
KONSOLE_SCHEME = "BubbleGumRave.colorscheme"
TMUX_MARKER_START = "# >>> steamdeck-workstation tmux >>>"
TMUX_MARKER_END = "# <<< steamdeck-workstation tmux <<<"
TOOLS = ("oh-my-posh", "starship", "zoxide", "fzf", "eza", "bat", "fastfetch", "tmux", "ghostty", "nvim", "opencode")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()



def newer_version(remote, installed):
    """Compare numbered release tags; do not downgrade or guess unfamiliar versions."""
    def parts(value):
        match = re.fullmatch(r'v?(\d+(?:\.\d+){0,3})', str(value or '').strip())
        return tuple(int(x) for x in match[1].split('.')) if match else None
    latest, current = parts(remote), parts(installed)
    if latest is None or current is None:
        return None
    return latest + (0,)*(4-len(latest)) > current + (0,)*(4-len(current))


def _request(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "deckctl-terminal/" + (core.ROOT / "VERSION").read_text().strip()})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(256 * 1024 * 1024 + 1)
        if len(data) > 256 * 1024 * 1024: raise RuntimeError("Terminal download exceeds size limit")
        return data


def _github_latest(repo: str) -> dict:
    data = _request(f"https://api.github.com/repos/{repo}/releases/latest", 30)
    return json.loads(data.decode("utf-8"))


def _github_asset(repo: str, pattern: str) -> tuple[dict, dict]:
    release = _github_latest(repo)
    rx = re.compile(pattern)
    matches = [a for a in release.get("assets", []) if rx.match(a.get("name", ""))]
    if len(matches) != 1:
        names = ", ".join(a.get("name", "") for a in release.get("assets", []))
        raise RuntimeError(f"Could not uniquely resolve {repo} asset /{pattern}/. Assets: {names[:800]}")
    return release, matches[0]


def _safe_tar_members(tf: tarfile.TarFile):
    members = tf.getmembers()
    if len(members) > 20000 or sum(m.size for m in members) > 512 * 1024 * 1024:
        raise RuntimeError("Terminal archive exceeds extraction limits")
    for m in members:
        p = Path(m.name)
        if m.name.startswith(("/", "\\")) or ".." in p.parts or not (m.isfile() or m.isdir()):
            raise RuntimeError(f"Unsafe archive member: {m.name}")
        yield m


def _select_archive_binary(members, binary: str, preferred_suffixes=()):
    """Choose one executable payload from release archives with duplicate basenames.

    Some upstream tarballs contain more than one file whose basename matches the
    executable (for example debug/rootfs copies). Prefer an explicitly documented
    runtime path such as /usr/bin/fastfetch, then a normal bin/ path, then only fall
    back to a unique basename match.
    """
    candidates = [m for m in members if m.isfile() and Path(m.name).name == binary]
    if not candidates:
        raise RuntimeError(f"archive did not contain a {binary} binary")

    normalized = [(m, "/" + m.name.lstrip("./")) for m in candidates]
    for suffix in preferred_suffixes:
        wanted = "/" + suffix.lstrip("/")
        matched = [m for m, name in normalized if name.endswith(wanted)]
        if matched:
            # Prefer the shallowest canonical runtime copy if an archive has more
            # than one matching rootfs/debug tree. Stable ordering makes retries
            # deterministic.
            matched.sort(key=lambda m: (len(Path(m.name).parts), m.name))
            return matched[0]

    bin_matches = [m for m, name in normalized if f"/bin/{binary}" in name and "/debug/" not in name]
    if bin_matches:
        bin_matches.sort(key=lambda m: (len(Path(m.name).parts), m.name))
        return bin_matches[0]

    if len(candidates) == 1:
        return candidates[0]

    names = ", ".join(m.name for m in candidates[:12])
    raise RuntimeError(f"archive contained multiple ambiguous {binary} binaries: {names}")


def _install_binary_asset(repo: str, pattern: str, binary: str, preferred_suffixes=(), verify_args=(), require_digest=False) -> dict:
    release, asset = _github_asset(repo, pattern)
    data = _request(asset["browser_download_url"], 90)
    archive_sha = _sha256_bytes(data)
    if require_digest and asset.get("digest") != "sha256:" + archive_sha:
        raise RuntimeError("Upstream asset SHA-256 missing or mismatched")
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf:
        members = list(_safe_tar_members(tf))
        chosen = _select_archive_binary(members, binary, preferred_suffixes)
        src = tf.extractfile(chosen)
        if src is None:
            raise RuntimeError(f"Could not read {binary} from {repo} archive")
        payload = src.read()
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    dest = BIN_DIR / binary
    fd, filename = tempfile.mkstemp(prefix=f'.{binary}-', dir=BIN_DIR)
    tmp = Path(filename)
    try:
        with os.fdopen(fd, 'wb') as stream: stream.write(payload)
        tmp.chmod(0o755)
        if verify_args:
            r = subprocess.run([str(tmp), *verify_args], text=True, capture_output=True, timeout=15)
            if r.returncode:
                detail = (r.stderr or r.stdout).strip()[-500:]
                raise RuntimeError(f"Installed {binary} failed verification: {detail}")
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)
    return {
        "source": repo,
        "version": release.get("tag_name"),
        "asset": asset.get("name"),
        "url": asset.get("browser_download_url"),
        "archive_sha256": archive_sha,
        "path": str(dest),
        "binary_sha256": _sha256_file(dest),
    }


def _install_appimage(repo: str, pattern: str, binary: str) -> dict:
    """Keep the full runtime; wrappers use extraction mode without requiring FUSE."""
    release, asset = _github_asset(repo, pattern)
    data = _request(asset["browser_download_url"], 120)
    digest = _sha256_bytes(data)
    if asset.get("digest") != "sha256:" + digest:
        raise RuntimeError("Upstream AppImage SHA-256 missing or mismatched")
    payload_dir = HOME / ".local/share/deckctl/terminal-appimages"
    payload_dir.mkdir(parents=True, exist_ok=True)
    payload = payload_dir / (binary + "-" + digest + ".AppImage")
    if payload.exists():
        if payload.is_symlink() or _sha256_file(payload) != digest:
            raise RuntimeError(f"Modified AppImage preserved: {payload}")
    else:
        fd, name = tempfile.mkstemp(prefix=".download-", dir=payload_dir)
        temp = Path(name)
        try:
            with os.fdopen(fd, "wb") as stream: stream.write(data)
            temp.chmod(0o755)
            env = {**os.environ, "APPIMAGE_EXTRACT_AND_RUN": "1"}
            result = subprocess.run([str(temp), "--version"], env=env, capture_output=True, text=True, timeout=60)
            if result.returncode:
                raise RuntimeError(f"{binary} failed version check: {result.stderr[-500:]}")
            temp.replace(payload)
        finally:
            temp.unlink(missing_ok=True)
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    dest = BIN_DIR / binary
    wrapper = '#!/bin/sh\nexec env APPIMAGE_EXTRACT_AND_RUN=1 ' + shlex.quote(str(payload)) + ' "$@"\n'
    fd, name = tempfile.mkstemp(prefix="." + binary + "-", dir=BIN_DIR)
    temp = Path(name)
    try:
        with os.fdopen(fd, "w") as stream: stream.write(wrapper)
        temp.chmod(0o755)
        temp.replace(dest)
    finally:
        temp.unlink(missing_ok=True)
    return {"source": repo, "version": release.get("tag_name"), "asset": asset["name"],
            "path": str(dest), "binary_sha256": _sha256_file(dest),
            "payload": str(payload), "payload_sha256": digest}


def _ghostty_desktop(create=True):
    # Unique deckctl entry; never replace an existing personal desktop entry.
    path = HOME / ".local/share/applications/deckctl-ghostty.desktop"
    executable = str(BIN_DIR / "ghostty").replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$").replace("%", "%%")
    text = '[Desktop Entry]\nType=Application\nName=Ghostty\nExec="' + executable + '"\nIcon=utilities-terminal\nTerminal=false\nCategories=System;TerminalEmulator;\n'
    if create and not path.exists() and not path.is_symlink() and (BIN_DIR / "ghostty").exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return path, text


def _run_official_installer(name: str, url: str, args: list[str]) -> dict:
    data = _request(url, 30)
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f'deckctl-{name}-') as folder:
        staging = Path(folder)
        script = staging/'install.sh'; script.write_bytes(data)
        output = staging/'bin'; output.mkdir()
        install_args = [str(output) if arg == str(BIN_DIR) else arg for arg in args]
        result = subprocess.run(['sh', str(script), *install_args], text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(f'{name} installer failed ({result.returncode}): {(result.stderr or result.stdout).strip()[-800:]}')
        candidate = output/name
        if not candidate.is_file() or candidate.is_symlink():
            raise RuntimeError(f'{name} installer did not produce a regular executable')
        version = subprocess.run([str(candidate), '--version'], text=True, capture_output=True, timeout=15)
        if version.returncode:
            raise RuntimeError(f'{name} failed its staged version check')
        match = re.search(r'\d+\.\d+(?:\.\d+)?', version.stdout)
        fd, filename = tempfile.mkstemp(prefix='.' + name + '-', dir=BIN_DIR)
        os.close(fd)
        temporary = Path(filename)
        try:
            shutil.copy2(candidate, temporary)
            temporary.replace(BIN_DIR/name)
        finally:
            temporary.unlink(missing_ok=True)
    return {'source': url, 'version': match[0] if match else None,
            'installer_sha256': _sha256_bytes(data), 'path': str(BIN_DIR/name),
            'binary_sha256': _sha256_file(BIN_DIR/name)}


def _install_oh_my_posh() -> dict:
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    return _run_official_installer(
        "oh-my-posh",
        "https://ohmyposh.dev/install.sh",
        ["-d", str(BIN_DIR)],
    )


def _install_starship() -> dict:
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    return _run_official_installer(
        "starship",
        "https://starship.rs/install.sh",
        ["-y", "-b", str(BIN_DIR)],
    )


def _install_zoxide() -> dict:
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    MAN_DIR.mkdir(parents=True, exist_ok=True)
    return _run_official_installer(
        "zoxide",
        "https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh",
        ["--bin-dir", str(BIN_DIR), "--man-dir", str(MAN_DIR)],
    )


def _install_fonts() -> dict:
    release, asset = _github_asset("ryanoasis/nerd-fonts", r"^JetBrainsMono\.tar\.xz$")
    url = asset["browser_download_url"]
    data = _request(url, 90)
    wanted = {
        "JetBrainsMonoNerdFontMono-Regular.ttf",
        "JetBrainsMonoNerdFontMono-Bold.ttf",
        "JetBrainsMonoNerdFontMono-Italic.ttf",
        "JetBrainsMonoNerdFontMono-BoldItalic.ttf",
    }
    FONT_DIR.mkdir(parents=True, exist_ok=True)
    installed = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:xz") as tf:
        members = list(_safe_tar_members(tf))
        chosen = [m for m in members if m.isfile() and Path(m.name).name in wanted]
        if not chosen:
            chosen = [m for m in members if m.isfile() and "JetBrainsMonoNerdFontMono" in Path(m.name).name and m.name.endswith(".ttf")][:12]
        if not chosen:
            raise RuntimeError("JetBrainsMono Nerd Font archive did not contain expected Mono TTF files")
        for m in chosen:
            src = tf.extractfile(m)
            if src is None:
                continue
            dest = FONT_DIR / Path(m.name).name
            dest.write_bytes(src.read())
            installed.append({"path": str(dest), "sha256": _sha256_file(dest)})
    if shutil.which("fc-cache"):
        subprocess.run(["fc-cache", "-f", str(FONT_DIR)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return {"source": url, "version": release.get("tag_name"), "archive_sha256": _sha256_bytes(data), "files": installed}


def _ghostty_config():
    directory = HOME / '.config/ghostty'
    directory.mkdir(parents=True, exist_ok=True)
    theme = directory / 'themes/deckctl-bubble-gum-rave'
    theme.parent.mkdir(parents=True, exist_ok=True)
    if not theme.is_symlink():
        shutil.copy2(core.ROOT / 'modules/terminal/ghostty-theme', theme)
    configs = [directory / name for name in ('config', 'config.ghostty')]
    if any(path.is_symlink() or (path.exists() and path.read_text().strip()) for path in configs):
        print('Existing Ghostty settings retained. Theme available: deckctl-bubble-gum-rave')
        return
    shutil.copy2(core.ROOT / 'modules/terminal/ghostty-config', directory / 'config.ghostty')


def _copy_managed_config(selected=None):
    TERM_CONFIG.mkdir(parents=True, exist_ok=True)
    SHELL_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    KONSOLE_DIR.mkdir(parents=True, exist_ok=True)
    src = core.ROOT / "modules/terminal"
    if selected is None:
        from . import component_options
        selected = set(component_options.defaults()['terminal'])
    files = {'starship': ('starship.toml', STARSHIP_CONFIG),
             'oh-my-posh': ('bubble-gum-rave.omp.json', POSH_CONFIG),
             'shell': ('terminal.sh', SHELL_CONFIG), 'tmux': ('tmux.conf', TMUX_CONFIG)}
    for key, (source, target) in files.items():
        if key in selected: shutil.copy2(src / source, target)
    if 'ghostty' in selected:
        _ghostty_config()
    if 'fastfetch' in selected:
        shutil.copy2(src / 'fastfetch.json', TERM_CONFIG / 'fastfetch.json')
    if 'shell' in selected:
        if not PROMPT_ENGINE_FILE.exists():
            PROMPT_ENGINE_FILE.write_text('posh\n' if 'oh-my-posh' in selected else 'starship\n')
        enabled = TERM_CONFIG / 'selected-tools'
        from . import component_options
        enabled.write_text('\n'.join(sorted(component_options.effective('terminal')))+'\n')
    if 'konsole' in selected:
        shutil.copy2(src / KONSOLE_PROFILE, KONSOLE_DIR / KONSOLE_PROFILE)
        shutil.copy2(src / KONSOLE_SCHEME, KONSOLE_DIR / KONSOLE_SCHEME)


def _replace_marker(path: Path, start: str, end: str, block: str):
    old = path.read_text() if path.exists() else ""
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end) + r"\n?", re.S)
    clean = pattern.sub("", old).rstrip()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text((clean + "\n\n" if clean else "") + block)


def _install_shell_block():
    block = (
        f"{SHELL_MARKER_START}\n"
        '[ -f "$HOME/.config/deckctl/shell/terminal.sh" ] && . "$HOME/.config/deckctl/shell/terminal.sh"\n'
        f"{SHELL_MARKER_END}\n"
    )
    _replace_marker(BASHRC, SHELL_MARKER_START, SHELL_MARKER_END, block)


def _install_tmux_block():
    block = (
        f"{TMUX_MARKER_START}\n"
        'source-file "$HOME/.config/deckctl/terminal/tmux.conf"\n'
        f"{TMUX_MARKER_END}\n"
    )
    _replace_marker(TMUXRC, TMUX_MARKER_START, TMUX_MARKER_END, block)


def _read_default_profile(text: str) -> str | None:
    in_desktop = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            in_desktop = line == "[Desktop Entry]"
            continue
        if in_desktop and line.startswith("DefaultProfile="):
            return line.split("=", 1)[1]
    return None


def _set_default_profile(path: Path, value: str | None):
    text = path.read_text() if path.exists() else ""
    lines = text.splitlines()
    out = []
    in_desktop = False
    desktop_seen = False
    key_written = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if in_desktop and not key_written and value is not None:
                out.append(f"DefaultProfile={value}")
                key_written = True
            in_desktop = stripped == "[Desktop Entry]"
            if in_desktop:
                desktop_seen = True
            out.append(line)
            continue
        if in_desktop and stripped.startswith("DefaultProfile="):
            if value is not None:
                out.append(f"DefaultProfile={value}")
                key_written = True
            continue
        out.append(line)
    if in_desktop and not key_written and value is not None:
        out.append(f"DefaultProfile={value}")
        key_written = True
    if not desktop_seen and value is not None:
        if out and out[-1] != "": out.append("")
        out.extend(["[Desktop Entry]", f"DefaultProfile={value}"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out).rstrip() + "\n")


def _set_konsole_default():
    state = core.load_json(STATE_FILE, {}) or {}
    if "konsole_previous_default" not in state:
        old = KONSOLERC.read_text() if KONSOLERC.exists() else ""
        state["konsolerc_existed"] = KONSOLERC.exists()
        state["konsole_previous_default"] = _read_default_profile(old)
        core.save_json(STATE_FILE, state)
    _set_default_profile(KONSOLERC, KONSOLE_PROFILE)


def _save_receipts(receipts: dict):
    receipts["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    core.save_json(RECEIPTS_FILE, receipts)


def _receipt_binary_ok(name: str, receipts: dict) -> bool:
    item = receipts.get(name, {})
    path = Path(item.get("path", "")) if item.get("path") else BIN_DIR / name
    expected = item.get("binary_sha256")
    payload_ok = True
    if item.get("payload"):
        payload = Path(item["payload"])
        payload_ok = payload.is_file() and not payload.is_symlink() and _sha256_file(payload) == item.get("payload_sha256")
    return bool(expected and path.exists() and _sha256_file(path) == expected and payload_ok)


def _unmanaged_local_binary(name: str, receipts: dict) -> bool:
    path = BIN_DIR / name
    expected = receipts.get(name, {}).get("binary_sha256")
    return path.is_symlink() or (path.exists() and (not expected or _sha256_file(path) != expected))


def _fonts_ok(receipts: dict) -> bool:
    files = receipts.get("fonts", {}).get("files", [])
    return bool(files) and all(Path(x.get("path", "")).exists() and x.get("sha256") and _sha256_file(Path(x["path"])) == x["sha256"] for x in files)



UPDATE_REPOS = {
    'oh-my-posh': 'JanDeDobbeleer/oh-my-posh', 'starship': 'starship/starship',
    'zoxide': 'ajeetdsouza/zoxide', 'fzf': 'junegunn/fzf', 'eza': 'eza-community/eza',
    'bat': 'sharkdp/bat', 'fastfetch': 'fastfetch-cli/fastfetch', 'tmux': 'tmux/tmux-builds',
    'ghostty': 'pkgforge-dev/ghostty-appimage', 'nvim': 'neovim/neovim',
    'opencode': 'anomalyco/opencode', 'fonts': 'ryanoasis/nerd-fonts',
}


def _tool_update_available(name, receipt):
    try:
        release = _github_latest(UPDATE_REPOS[name])
        current = receipt.get('version')
        if not current and name != 'fonts':
            result = subprocess.run([str(BIN_DIR/name), '--version'], capture_output=True, text=True, timeout=15)
            match = re.search(r'\d+\.\d+(?:\.\d+)?', result.stdout)
            current = match[0] if match else None
        newer = newer_version(release.get('tag_name'), current)
        if newer is None:
            if name == 'fonts' and not current:
                asset = next((a for a in release.get('assets', []) if a['name'] == 'JetBrainsMono.tar.xz'), {})
                digest = asset.get('digest')
                if digest and receipt.get('archive_sha256'):
                    return digest != 'sha256:' + receipt['archive_sha256']
            print(f'    cannot compare {name} release versions; existing tool retained')
            return False
        return newer
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'    update check unavailable; installed {name} retained: {exc}')
        return False


def apply(config_only: bool = False, refresh: bool = False, only=None) -> int:
    if os.geteuid() == 0 and os.environ.get("DECKCTL_ALLOW_ROOT_TEST") != "1":
        print("Do not run terminal setup as root. Everything is installed in the deck user's home directory.")
        return 2
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    receipts = core.load_json(RECEIPTS_FILE, {}) or {}
    from . import component_options
    selected = component_options.effective('terminal')
    if only is not None:
        if only not in selected: raise ValueError('Terminal tool is not selected: '+only)
        selected = {only}
    failures = []
    if not config_only:
        installers = [
            ("oh-my-posh", _install_oh_my_posh),
            ("starship", _install_starship),
            ("zoxide", _install_zoxide),
            ("fzf", lambda: _install_binary_asset("junegunn/fzf", r"^fzf-[^-]+-linux_amd64\.tar\.gz$", "fzf")),
            ("eza", lambda: _install_binary_asset("eza-community/eza", r"^eza_x86_64-unknown-linux-gnu\.tar\.gz$", "eza")),
            ("bat", lambda: _install_binary_asset("sharkdp/bat", r"^bat-v.*-x86_64-unknown-linux-gnu\.tar\.gz$", "bat")),
            ("fastfetch", lambda: _install_binary_asset("fastfetch-cli/fastfetch", r"^fastfetch-linux-amd64\.tar\.gz$", "fastfetch", ("usr/bin/fastfetch",), ("--version",))),
            ("tmux", lambda: _install_binary_asset("tmux/tmux-builds", r"^tmux-.*-linux-x86_64\.tar\.gz$", "tmux")),
            ("ghostty", lambda: _install_appimage("pkgforge-dev/ghostty-appimage", r"^Ghostty-.*-x86_64\.AppImage$", "ghostty")),
            ("nvim", lambda: _install_appimage("neovim/neovim", r"^nvim-linux-x86_64\.appimage$", "nvim")),
            ("opencode", lambda: _install_binary_asset("anomalyco/opencode", r"^opencode-linux-x64-baseline\.tar\.gz$", "opencode", verify_args=("--version",), require_digest=True)),
            ("fonts", _install_fonts),
        ]
        for name, fn in installers:
            if name not in selected: continue
            try:
                print(f"==> terminal: {name}")
                if name == "fonts":
                    if _fonts_ok(receipts) and not _tool_update_available(name, receipts.get(name, {})):
                        print("    healthy; skipped")
                        continue
                else:
                    if _receipt_binary_ok(name, receipts) and not _tool_update_available(name, receipts.get(name, {})):
                        print("    healthy; skipped")
                        continue
                    if _unmanaged_local_binary(name, receipts):
                        print(f"    existing unmanaged {BIN_DIR/name}; preserved (not overwritten)")
                        continue
                receipts[name] = fn()
                print("    installed")
            except Exception as exc:
                failures.append((name, str(exc)))
                print(f"    WARN: {exc}")
        _save_receipts(receipts)
    _copy_managed_config(selected)
    if 'shell' in selected: _install_shell_block()
    if 'tmux' in selected: _install_tmux_block()
    if 'konsole' in selected: _set_konsole_default()
    if 'ghostty' in selected: _ghostty_desktop()
    print("Applied selected terminal tools and configuration.")
    print("Only selected tools and appearance settings are applied.")
    if "shell" in selected:
        print("Open a new terminal to activate selected shell integrations.")
    if failures:
        print("\nSome optional terminal payloads could not be downloaded:")
        for name, err in failures:
            print(f"- {name}: {err}")
        print("Rerun later with: deckctl terminal apply")
        return 1
    return 0


def _shell_block_present() -> bool:
    try:
        return SHELL_MARKER_START in BASHRC.read_text() and SHELL_MARKER_END in BASHRC.read_text()
    except FileNotFoundError:
        return False


def _tmux_block_present() -> bool:
    try:
        return TMUX_MARKER_START in TMUXRC.read_text() and TMUX_MARKER_END in TMUXRC.read_text()
    except FileNotFoundError:
        return False


def _font_match() -> str | None:
    if not shutil.which("fc-match"):
        return None
    try:
        r = subprocess.run(["fc-match", "-f", "%{family}\n", "JetBrainsMono Nerd Font Mono"], text=True, capture_output=True, timeout=5)
        return (r.stdout or "").splitlines()[0].strip() if r.returncode == 0 and r.stdout.strip() else None
    except Exception:
        return None


def _prompt_engine() -> str:
    try:
        value = PROMPT_ENGINE_FILE.read_text().strip().lower()
    except FileNotFoundError:
        value = "posh"
    return value if value in {"posh", "starship"} else "posh"


def prompt_status() -> int:
    engine = _prompt_engine()
    print("TERMINAL PROMPT")
    print(f"Active engine     {engine}")
    print(f"Oh My Posh        {'READY' if (shutil.which('oh-my-posh') or (BIN_DIR/'oh-my-posh').exists()) else 'MISSING'}")
    print(f"Starship          {'READY' if (shutil.which('starship') or (BIN_DIR/'starship').exists()) else 'MISSING'}")
    print(f"Posh theme        {'READY' if POSH_CONFIG.exists() else 'MISSING'} {POSH_CONFIG}")
    print(f"Starship theme    {'READY' if STARSHIP_CONFIG.exists() else 'MISSING'} {STARSHIP_CONFIG}")
    return 0


def prompt_use(engine: str) -> int:
    engine = engine.lower()
    if engine not in {"posh", "starship"}:
        print("Prompt engine must be: posh or starship")
        return 2
    TERM_CONFIG.mkdir(parents=True, exist_ok=True)
    PROMPT_ENGINE_FILE.write_text(engine + "\n")
    print(f"Terminal prompt set to {engine}.")
    print("Open a new Konsole window or run: source ~/.config/deckctl/shell/terminal.sh")
    return 0


def status_data() -> dict:
    from . import component_options
    selected = component_options.effective('terminal')
    command_state = {}
    for tool in TOOLS:
        if tool not in selected: continue
        found = shutil.which(tool)
        p = found or (str(BIN_DIR / tool) if (BIN_DIR / tool).exists() else None)
        ready = bool(p and Path(p).exists())
        if ready and tool in ("ghostty", "nvim", "opencode"):
            try:
                ready = subprocess.run([p, "--version"], capture_output=True, timeout=15).returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                ready = False
        command_state[tool] = {"ready": ready, "path": p}
    font = _font_match()
    data = {
        "selected": sorted(selected),
        "commands": command_state,
        "font": {"ready": FONT_DIR.exists() and any(FONT_DIR.glob("*.ttf")), "match": font, "path": str(FONT_DIR)},
        "starship_config": STARSHIP_CONFIG.exists(),
        "posh_config": POSH_CONFIG.exists(),
        "prompt_engine": _prompt_engine(),
        "shell_config": SHELL_CONFIG.exists() and _shell_block_present(),
        "konsole_profile": (KONSOLE_DIR / KONSOLE_PROFILE).exists(),
        "konsole_scheme": (KONSOLE_DIR / KONSOLE_SCHEME).exists(),
        "konsole_default": _read_default_profile(KONSOLERC.read_text() if KONSOLERC.exists() else "") == KONSOLE_PROFILE,
        "tmux_config": TMUX_CONFIG.exists() and _tmux_block_present(),
    }
    ready_count = sum(1 for v in command_state.values() if v["ready"])
    requirements = {'starship': ['starship_config'], 'oh-my-posh': ['posh_config'], 'shell': ['shell_config'],
                    'konsole': ['konsole_profile', 'konsole_scheme', 'konsole_default'], 'tmux': ['tmux_config']}
    all_cfg = all(data[k] for item in selected for k in requirements.get(item, []))
    if ready_count == len(command_state) and ('fonts' not in selected or data['font']['ready']) and all_cfg:
        data["status"] = "READY"
        data["message"] = "Selected terminal tools and settings are ready"
    elif ready_count == 0 and not all_cfg:
        data["status"] = "NOT_INSTALLED"
        data["message"] = "Terminal polish/toolbox is not installed"
    else:
        missing = [k for k, v in command_state.items() if not v["ready"]]
        data["status"] = "DEGRADED"
        data["message"] = "Terminal setup is partial" + (f"; missing: {', '.join(missing)}" if missing else "")
    return data


def status(as_json: bool = False) -> int:
    data = status_data()
    if as_json:
        print(json.dumps(data, indent=2))
        return 0 if data["status"] == "READY" else 1
    print("BUBBLE GUM RAVE TERMINAL")
    print(f"Status             {data['status']}")
    selected = set(data['selected'])
    for option, label, ready in [
            ('konsole','Konsole appearance',data['konsole_profile'] and data['konsole_scheme'] and data['konsole_default']),
            ('fonts','Nerd Font',data['font']['ready']), ('oh-my-posh','Oh My Posh theme',data['posh_config']),
            ('starship','Starship config',data['starship_config']), ('shell','Bash integration',data['shell_config']),
            ('tmux','tmux config',data['tmux_config'])]:
        state = 'NOT SELECTED' if option not in selected else 'READY' if ready else 'MISSING'
        print(f'{label:<20} {state}')
    print("\nTOOLS")
    for name, item in data["commands"].items():
        print(f"{name:<12} {'READY' if item['ready'] else 'MISSING':<8} {item['path'] or ''}")
    print("\nPrompt: Oh My Posh is default. Switch with `deckctl terminal prompt use posh|starship`.")
    print("Shortcuts: ll, lt, c, .., ..., gs, gd, gl, ff; z/zi come from zoxide; Ctrl-R/Ctrl-T/Alt-C come from fzf.")
    print("tmux: tm=create/attach main, tml=list, tma=attach, tmk=kill (asks), tmhelp=key cheat sheet.")
    return 0 if data["status"] == "READY" else 1


def tmux_status() -> int:
    binary = shutil.which("tmux") or (str(BIN_DIR / "tmux") if (BIN_DIR / "tmux").exists() else None)
    ready_binary = bool(binary and Path(binary).exists())
    ready_config = TMUX_CONFIG.exists() and _tmux_block_present()
    print("TMUX")
    print(f"Binary            {'READY' if ready_binary else 'MISSING'} {binary or ''}")
    if ready_binary:
        try:
            r = subprocess.run([binary, "-V"], text=True, capture_output=True, timeout=5)
            print(f"Version           {(r.stdout or r.stderr).strip()}")
        except Exception:
            pass
    print(f"Managed config    {'READY' if ready_config else 'MISSING'}")
    if ready_binary:
        r = subprocess.run([binary, "list-sessions"], text=True, capture_output=True)
        if r.returncode == 0:
            print("\nSessions:")
            print(r.stdout.rstrip())
        else:
            print("\nSessions: none running")
    print("\nStart/attach: tm")
    print("Cheat sheet:  tmhelp")
    return 0 if ready_binary and ready_config else 1


def tmux_apply() -> int:
    if os.geteuid() == 0 and os.environ.get("DECKCTL_ALLOW_ROOT_TEST") != "1":
        print("Do not run tmux setup as root; it is installed in the deck user's home directory.")
        return 2
    receipts = core.load_json(RECEIPTS_FILE, {}) or {}
    try:
        if _receipt_binary_ok("tmux", receipts):
            print("tmux binary healthy; skipped")
        elif _unmanaged_local_binary("tmux", receipts):
            print(f"Existing unmanaged {BIN_DIR/'tmux'} preserved (not overwritten)")
        else:
            print("==> terminal: tmux")
            receipts["tmux"] = _install_binary_asset("tmux/tmux-builds", r"^tmux-.*-linux-x86_64\.tar\.gz$", "tmux")
            _save_receipts(receipts)
            print("    installed")
    except Exception as exc:
        print(f"tmux install failed: {exc}")
        return 1
    _copy_managed_config({"tmux"})
    _install_tmux_block()
    print("tmux configuration applied. Existing tmux servers should be restarted after a tmux binary upgrade (`tmux kill-server`).")
    return 0


def font_check() -> int:
    print(f"Managed font directory: {FONT_DIR}")
    fonts = sorted(FONT_DIR.glob("*.ttf")) if FONT_DIR.exists() else []
    for p in fonts:
        print(f"- {p.name}")
    match = _font_match()
    print(f"fc-match: {match or 'unavailable / no match'}")
    return 0 if fonts else 1


def _remove_marker(path: Path, start: str, end: str):
    if not path.exists():
        return
    text = path.read_text()
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end) + r"\n?", re.S)
    path.write_text(pattern.sub("", text).rstrip() + ("\n" if text else ""))


def reset(keep_tools: bool = False) -> int:
    _remove_marker(BASHRC, SHELL_MARKER_START, SHELL_MARKER_END)
    _remove_marker(TMUXRC, TMUX_MARKER_START, TMUX_MARKER_END)
    SHELL_CONFIG.unlink(missing_ok=True)
    TMUX_CONFIG.unlink(missing_ok=True)
    if STARSHIP_CONFIG.exists():
        STARSHIP_CONFIG.unlink()
    if POSH_CONFIG.exists():
        POSH_CONFIG.unlink()
    PROMPT_ENGINE_FILE.unlink(missing_ok=True)
    for p in (KONSOLE_DIR / KONSOLE_PROFILE, KONSOLE_DIR / KONSOLE_SCHEME):
        p.unlink(missing_ok=True)
    state = core.load_json(STATE_FILE, {}) or {}
    previous = state.get("konsole_previous_default")
    if KONSOLERC.exists():
        _set_default_profile(KONSOLERC, previous)
    if not keep_tools:
        receipts = core.load_json(RECEIPTS_FILE, {}) or {}
        for name in TOOLS:
            item = receipts.get(name, {})
            p = Path(item.get("path", "")) if item.get("path") else None
            expected = item.get("binary_sha256")
            if p and p == BIN_DIR / name and not p.is_symlink() and p.is_file() and expected and _sha256_file(p) == expected:
                p.unlink()
                print(f"Removed managed {name}: {p}")
            elif p and p.exists():
                print(f"Kept modified/untracked {name}: {p}")
        for item in receipts.get("fonts", {}).get("files", []):
            p = Path(item.get("path", ""))
            if p.parent == FONT_DIR and not p.is_symlink() and p.is_file() and item.get("sha256") and _sha256_file(p) == item["sha256"]:
                p.unlink()
        try:
            if FONT_DIR.exists() and not any(FONT_DIR.iterdir()): FONT_DIR.rmdir()
        except Exception:
            pass
        if shutil.which("fc-cache"):
            subprocess.run(["fc-cache", "-f"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    desktop, expected = _ghostty_desktop(create=False)
    if not keep_tools and not (BIN_DIR / "ghostty").exists() and desktop.is_file() and not desktop.is_symlink():
        if desktop.read_text() == expected:
            desktop.unlink()
    print("Terminal customization reset. Personal editor settings and downloaded AppImages are retained. Open a new Konsole window.")
    return 0
