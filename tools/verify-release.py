#!/usr/bin/env python3
"""Verify final checksums, independent extractions, nested USB repo, modes and tests."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import stat
import subprocess
import argparse
import sys
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'lib'))
from deckctl.install_log import redact
JUNK = {'.git', '__pycache__', 'release', 'support-bundles', '.pytest_cache'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_name(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name:
        raise ValueError('Unsafe archive member: ' + name)
    if any(part in JUNK for part in p.parts) or p.suffix in ('.pyc', '.pyo', '.tmp', '.log'):
        raise ValueError('Build junk in archive: ' + name)
    return p


def extract_tar(archive, destination, version):
    prefix = f'steamdeck-workstation-{version}'
    with tarfile.open(archive, 'r:gz') as tar:
        seen = set()
        for member in tar.getmembers():
            name = safe_name(member.name)
            if not name.parts or name.parts[0] != prefix or member.name in seen:
                raise ValueError('Unexpected/duplicate repo archive entry: ' + member.name)
            seen.add(member.name)
            if not member.isfile() and not member.isdir():
                raise ValueError('Unsupported archive member: ' + member.name)
        # All types and names are checked above; use platform tar for mode preservation.
    destination.mkdir()
    subprocess.run(['tar', '--no-same-owner', '-xzf', str(archive), '-C', str(destination)], check=True)
    return destination / prefix


def inventory(root):
    return {str(p.relative_to(root)): (digest(p), p.stat().st_mode & 0o777) for p in root.rglob('*') if p.is_file() and not any(x in JUNK for x in p.relative_to(root).parts) and p.suffix not in ('.pyc', '.pyo')}


def validate_tree(tree, version, log):
    if (tree / 'VERSION').read_text().strip() != version:
        raise ValueError('Wrong extracted release version')
    for entry in ('install.sh', 'bin/deckctl', 'tools/build-release', 'tools/package-release.py', 'tools/verify-release.py'):
        if not os.access(tree / entry, os.X_OK): raise ValueError('Missing executable: ' + entry)
    try:
        with log.open('w') as output:
            subprocess.run([str(tree / 'bin/deckctl'), 'repo', 'validate'], cwd=tree, stdout=output, stderr=subprocess.STDOUT, check=True)
    except subprocess.CalledProcessError:
        with log.open('rb') as output:
            output.seek(max(0, log.stat().st_size-24000))
            tail = output.read().decode('utf-8', errors='replace')
        print('Extracted release validation failed. Recent test output:\n'+redact(tail), file=sys.stderr)
        raise


def main():
    parser=argparse.ArgumentParser(description='Verify delivered release archives and checksums in independent clean extractions.', epilog='Checks USB layout, nested archive identity, modes, source inventory, and runs repository regressions in both extracted copies. Exit 0 only if every gate passes.')
    parser.add_argument('output', help='Directory containing the three final release artifacts.')
    out = Path(parser.parse_args().output).resolve()
    version = (ROOT / 'VERSION').read_text().strip()
    tar_name = f'steamdeck-workstation-v{version}.tar.gz'
    zip_name = f'STEAMDECK-SETUP-v{version}.zip'
    checksum = out / f'steamdeck-workstation-v{version}-SHA256SUMS.txt'
    expected = {}
    for line in checksum.read_text().splitlines():
        sha, name = line.split('  ', 1)
        if name in expected: raise ValueError('Duplicate checksum entry')
        expected[name] = sha
    if set(expected) != {tar_name, zip_name}: raise ValueError('Unexpected checksum contents')
    for name, sha in expected.items():
        if digest(out / name) != sha: raise ValueError('Checksum mismatch: ' + name)
    with tempfile.TemporaryDirectory(prefix='deckctl-package-verify-') as temporary:
        work = Path(temporary)
        tree = extract_tar(out / tar_name, work / 'repo', version)
        before = inventory(tree)
        # When called from the build tree, compare every delivered source byte/mode.
        source = inventory(ROOT)
        source = {n: v for n, v in source.items() if out not in (ROOT / n).parents}
        if before != source:
            raise ValueError('Packaged repo differs from source inventory: ' + str(sorted(set(before) ^ set(source))))
        validate_tree(tree, version, work / 'repo-validation.log')
        usb = work / 'usb'; usb.mkdir()
        wanted = {'STEAMDECK-SETUP/' + n for n in ('README-FIRST.txt', 'INSTALL.sh', 'SHA256SUMS', tar_name)}
        with zipfile.ZipFile(out / zip_name) as archive:
            if archive.testzip() is not None: raise ValueError('ZIP CRC verification failed')
            if set(archive.namelist()) != wanted or len(archive.namelist()) != len(wanted): raise ValueError('Unexpected USB layout')
            for member in archive.infolist():
                rel = safe_name(member.filename)
                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode): raise ValueError('USB ZIP contains a symlink')
                target = usb.joinpath(*rel.parts); target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(member)); target.chmod(mode & 0o777)
        bundle = usb / 'STEAMDECK-SETUP'
        if not os.access(bundle / 'INSTALL.sh', os.X_OK): raise ValueError('USB installer lost executable permissions')
        subprocess.run(['bash', '-n', str(bundle / 'INSTALL.sh')], check=True)
        if f'v{version}' not in (bundle / 'README-FIRST.txt').read_text(): raise ValueError('USB README has wrong version')
        subprocess.run(['sha256sum', '--check', '--strict', 'SHA256SUMS'], cwd=bundle, check=True)
        if digest(bundle / tar_name) != expected[tar_name]: raise ValueError('USB nested repo differs from standalone tar')
        nested = extract_tar(bundle / tar_name, work / 'nested', version)
        if inventory(nested) != before: raise ValueError('Independent extracted repo inventories differ')
        validate_tree(nested, version, work / 'nested-validation.log')
        print(json.dumps({'version': version, 'repository_files': len(before), 'independent_extractions': 2, 'usb_layout': 'PASS', 'nested_archive_identity': 'PASS', 'executable_permissions': 'PASS', 'repository_tests_both_copies': 'PASS', 'sha256': 'PASS', 'checksums': expected}, indent=2))


if __name__ == '__main__':
    main()
