from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def battlenet_candidates(home: Path | None = None):
    home = home or Path.home()
    base = home / ".local/share/Steam/steamapps/compatdata"
    rels = (
        "pfx/drive_c/Program Files (x86)/Battle.net/Battle.net Launcher.exe",
        "pfx/drive_c/Program Files (x86)/Battle.net/Battle.net.exe",
    )
    out = []
    for prefix in ("NonSteamLaunchers", "Battle.netLauncher"):
        for rel in rels:
            out.append(base / prefix / rel)
    return out


def battlenet_path(home: Path | None = None):
    for p in battlenet_candidates(home):
        if p.exists():
            return p
    return None


def battlenet_installed(home: Path | None = None) -> bool:
    return battlenet_path(home) is not None


def install_battlenet() -> int:
    """Run NSL's supported targeted launcher install for Battle.net only."""
    script = ROOT / "modules/gaming/install-battlenet.sh"
    return subprocess.run([str(script)]).returncode
