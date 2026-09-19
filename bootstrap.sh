#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'HELP'
NAME
  bootstrap.sh — Download and verify the public Steam Deck Workstation release.
SYNOPSIS
  bash bootstrap.sh [--version X.Y.Z] [--download-only DIRECTORY]
DESCRIPTION
  Downloads the latest stable release (or a specified version) from
  Samuel-Bartels-Dev/steamdeck-workstation on GitHub. Verifies the release tar
  against SHA256SUMS, safely extracts it with executable modes, then launches
  install.sh as your normal user with terminal input. Never run with sudo.
  --download-only saves the verified archive and checksum without installation.
  Requires Python 3 and internet. No account is needed for public downloads.
EXIT STATUS
  0 on success; nonzero for missing releases, download/checksum errors or failure.
HELP
  exit 0
fi
command -v python3 >/dev/null || { echo 'Python 3 is required.' >&2; exit 1; }
if [[ $EUID -eq 0 ]]; then echo 'Run as your normal user, without sudo.' >&2; exit 1; fi
python3 - "$@" <<'PY'
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

REPO='Samuel-Bartels-Dev/steamdeck-workstation'

def fetch(url,limit):
    request=urllib.request.Request(url,headers={'User-Agent':'steamdeck-workstation-bootstrap'})
    with urllib.request.urlopen(request,timeout=90) as response:
        data=response.read(limit+1)
    if len(data)>limit:raise ValueError('Download exceeds size limit')
    return data

def resolve(version=None):
    if version and not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('Version must be X.Y.Z')
    endpoint='tags/v'+version if version else 'latest'
    release=json.loads(fetch(f'https://api.github.com/repos/{REPO}/releases/{endpoint}',4*1024*1024))
    tag=release.get('tag_name','')
    if not re.fullmatch(r'v\d+\.\d+\.\d+',tag) or release.get('draft') or release.get('prerelease'):
        raise ValueError('Expected a published stable versioned release')
    if version and tag!='v'+version:raise ValueError('Requested release version mismatch')
    version=tag[1:]
    names=[f'steamdeck-workstation-v{version}.tar.gz',f'steamdeck-workstation-v{version}-SHA256SUMS.txt']
    assets={}
    for name in names:
        matches=[a for a in release.get('assets',[]) if a.get('name')==name]
        if len(matches)!=1:raise ValueError(f'Release asset missing or ambiguous: {name}')
        url=matches[0].get('browser_download_url','')
        if url!=f'https://github.com/{REPO}/releases/download/{tag}/{name}':raise ValueError('Unexpected release asset URL')
        assets[name]=url
    return version,assets

def download(work,version,assets):
    tarname=f'steamdeck-workstation-v{version}.tar.gz'
    sumsname=f'steamdeck-workstation-v{version}-SHA256SUMS.txt'
    sums=fetch(assets[sumsname],1024*1024)
    matches=[line.split('  ',1)[0] for line in sums.decode().splitlines() if line.endswith('  '+tarname)]
    if len(matches)!=1 or not re.fullmatch('[0-9a-fA-F]{64}',matches[0]):raise ValueError('Missing/ambiguous SHA-256 entry')
    archive=work/tarname
    request=urllib.request.Request(assets[tarname],headers={'User-Agent':'steamdeck-workstation-bootstrap'})
    total=0;digest=hashlib.sha256()
    with urllib.request.urlopen(request,timeout=90) as response,archive.open('wb') as out:
        while True:
            block=response.read(1024*1024)
            if not block:break
            total+=len(block)
            if total>512*1024*1024:raise ValueError('Archive exceeds size limit')
            digest.update(block);out.write(block)
    if digest.hexdigest()!=matches[0].lower():raise ValueError('SHA-256 mismatch; installation blocked')
    (work/sumsname).write_bytes(sums)
    return archive

def extract(archive,work,version):
    prefix=f'steamdeck-workstation-{version}'
    with tarfile.open(archive,'r:gz') as tf:
        members=tf.getmembers();seen=set()
        if len(members)>20000 or sum(m.size for m in members)>512*1024*1024:raise ValueError('Extraction budget exceeded')
        for member in members:
            path=Path(member.name)
            if not path.parts or path.parts[0]!=prefix or path.is_absolute() or '..' in path.parts or '\\' in member.name or not (member.isfile() or member.isdir()) or str(path) in seen:
                raise ValueError('Unsafe archive entry')
            seen.add(str(path))
        tf.extractall(work,filter='data')
    root=work/prefix
    if (root/'VERSION').read_text().strip()!=version:raise ValueError('Extracted version mismatch')
    if not (root/'install.sh').is_file() or not os.access(root/'bin/deckctl',os.X_OK):raise ValueError('Installer entry points missing or non-executable')
    return root

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--version');parser.add_argument('--download-only')
    args=parser.parse_args()
    version,assets=resolve(args.version)
    with tempfile.TemporaryDirectory(prefix='deckctl-bootstrap-') as temporary:
        work=Path(temporary);archive=download(work,version,assets)
        root=extract(archive,work,version)
        print(f'Steam Deck Workstation {version}: archive SHA-256 and layout verified.',flush=True)
        if args.download_only:
            destination=Path(args.download_only).expanduser();destination.mkdir(parents=True,exist_ok=True)
            for name in assets:
                target=destination/name
                if target.exists() or target.is_symlink():raise ValueError(f'Destination already exists: {target}')
            for name in assets:shutil.copy2(work/name,destination/name)
            return 0
        with open('/dev/tty','r') as terminal:
            return subprocess.run(['bash',str(root/'install.sh')],cwd=root,stdin=terminal).returncode

if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as exc:raise SystemExit(f'Bootstrap stopped: {exc}')
PY
