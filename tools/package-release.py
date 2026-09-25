#!/usr/bin/env python3
"""Build the repository tar, established USB wrapper, and final SHA-256 manifest."""
from pathlib import Path
import hashlib
import os
import re
import shutil
import subprocess
import argparse
import sys
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {'.git', '__pycache__', 'release', 'support-bundles', '.pytest_cache'}


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__, epilog='Runs repository validation first. Writes exactly the versioned repo tar, USB ZIP with installer/nested archive, and SHA256SUMS. Then run tools/verify-release.py on the output directory.')
    parser.add_argument('output', nargs='?', default=str(ROOT/'release'), help='Output directory (default: release/). Existing same-version artifacts are replaced only after building the new set.')
    args=parser.parse_args()
    version = (ROOT / 'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-rc[1-9]\d*)?', version):
        raise SystemExit('Invalid release version')
    out = Path(args.output).resolve()
    if out == ROOT or out in ROOT.parents:
        raise SystemExit('Output must not be the source tree or a parent of it')
    subprocess.run([str(ROOT / 'bin/deckctl'), 'repo', 'validate'], check=True)
    name = f'steamdeck-workstation-{version}'
    tar_name = f'steamdeck-workstation-v{version}.tar.gz'
    zip_name = f'STEAMDECK-SETUP-v{version}.zip'
    sum_name = f'steamdeck-workstation-v{version}-SHA256SUMS.txt'
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.deckctl-release-', dir=out) as temporary:
        work = Path(temporary)
        tar_path = work / tar_name
        # Explicit per-file inventory prevents recursive inclusion of an output folder.
        with tarfile.open(tar_path, 'w:gz', format=tarfile.PAX_FORMAT) as archive:
            for path in [ROOT] + sorted(ROOT.rglob('*')):
                rel = path.relative_to(ROOT)
                if any(p in EXCLUDE for p in rel.parts) or path.suffix in {'.pyc', '.pyo'} or path == out or out in path.parents:
                    continue
                if path.is_symlink():
                    raise RuntimeError(f'Release source must not contain symlinks: {rel}')
                archive.add(path, arcname=str(Path(name) / rel), recursive=False)
        usb = work / 'STEAMDECK-SETUP'
        usb.mkdir()
        shutil.copy2(tar_path, usb / tar_name)
        (usb / 'SHA256SUMS').write_text(f'{digest(tar_path)}  {tar_name}\n')
        (usb / 'README-FIRST.txt').write_text(f'''Steam Deck Workstation v{version}

1. Complete Valve setup/updates and switch to Desktop Mode.
2. Extract this entire STEAMDECK-SETUP folder from the ZIP.
3. Open Konsole in this folder and run: bash INSTALL.sh

INSTALL.sh verifies the nested archive, extracts it with Unix permissions,
and runs the normal installer. Do not run it with sudo. The normal installer
keeps a persistent local copy and deckctl command; the USB can be removed afterward.
Internet is required for Flatpaks, Decky plugins, CSS Theme Store components,
and other vendor downloads. This is a delivery bundle, not an offline payload cache.
Use the external steamdeck-workstation-v{version}-SHA256SUMS.txt to verify
both delivered archives. The SHA256SUMS inside this folder verifies its nested repo.

Bubble Gum Rave is configuration for real CSS Loader themes, never a standalone
theme. SteamGridDB manages Gaming Mode artwork. Desktop icons are bundled.
''')
        installer = usb / 'INSTALL.sh'
        installer.write_text(f'''#!/usr/bin/env bash
set -euo pipefail
if [[ "${{1:-}}" == "--help" || "${{1:-}}" == "-h" ]]; then
  cat <<'HELP'
NAME
  INSTALL.sh — Install Steam Deck Workstation from this USB bundle.
SYNOPSIS
  bash INSTALL.sh
DESCRIPTION
  Verify SHA256SUMS, extract the repository with executable permissions,
  and run the normal guided installer as the Deck user. Internet is required
  for vendor payloads. The persistent installed copy survives USB removal.
EXIT STATUS
  0 on completion; nonzero if verification or installation fails.
HELP
  exit 0
fi
if [[ $EUID -eq 0 ]]; then echo "Run this installer as the normal Deck user, without sudo." >&2; exit 1; fi
USB_ROOT="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
cd "$USB_ROOT"
sha256sum --check --strict SHA256SUMS
EXTRACT_ROOT="$(mktemp -d)"
trap 'rm -rf "$EXTRACT_ROOT"' EXIT
tar --no-same-owner -xzf "{tar_name}" -C "$EXTRACT_ROOT"
test "$(cat "$EXTRACT_ROOT/{name}/VERSION")" = "{version}"
bash "$EXTRACT_ROOT/{name}/install.sh"
''')
        installer.chmod(0o755)
        with zipfile.ZipFile(work / zip_name, 'w', zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(usb.rglob('*')):
                if path.is_file():
                    archive.write(path, path.relative_to(work))
        (work / sum_name).write_text(''.join(f'{digest(work / n)}  {n}\n' for n in [tar_name, zip_name]))
        for filename in (tar_name, zip_name, sum_name):
            os.replace(work / filename, out / filename)
            print(out / filename)


if __name__ == '__main__':
    main()
