#!/usr/bin/env python3
"""Require exact source fingerprint and documented validation before stable publishing."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
GATES = ('ci', 'unit', 'integration', 'compatibility', 'storage', 'fresh_install',
         'idempotency', 'upgrade', 'interrupted_install', 'dirty_state_repair', 'health',
         'reboot', 'desktop_mode', 'gaming_mode', 'support_bundle', 'public_bootstrap')


def fingerprint():
    digest = hashlib.sha256()
    # Exclude version/docs/evidence to allow RC -> stable promotion without claiming
    # that changing implementation after testing is safe. Modes are significant.
    paths = []
    for name in ('lib', 'modules', 'config', 'compatibility', 'bin', 'tools', 'host', 'profiles', 'tests', '.github'):
        paths.extend(p for p in (ROOT/name).rglob('*') if p.is_file())
    paths.extend(ROOT/name for name in ('bootstrap.sh', 'install.sh', 'uninstall.sh'))
    for p in sorted(paths):
        if '__pycache__' in p.parts or p.suffix in ('.pyc', '.pyo'): continue
        if p.is_symlink(): raise ValueError('Symlinks not allowed in release sources')
        digest.update(str(p.relative_to(ROOT)).encode()+b'\0')
        digest.update(str(p.stat().st_mode & 0o777).encode()+b'\0')
        digest.update(p.read_bytes()+b'\0')
    return digest.hexdigest()


def validate(report, version, source):
    if report.get('schema_version') != 1 or report.get('version') != version:
        raise ValueError('Missing or wrong-version release evidence')
    if report.get('source_sha256') != source: raise ValueError('Source differs from validated candidate')
    if not re.fullmatch(re.escape(version)+r'-rc[1-9]\d*', report.get('candidate', '')):
        raise ValueError('Evidence must identify a release candidate for this version')
    for field in ('date', 'tester', 'hardware', 'steamos', 'kernel', 'decky'):
        if not isinstance(report.get(field), str) or not report[field].strip(): raise ValueError('Missing evidence field: '+field)
    for gate in GATES:
        row = report.get('gates', {}).get(gate, {})
        if row.get('status') != 'PASS' or not isinstance(row.get('evidence'), str) or not row['evidence'].strip():
            raise ValueError('Stable release blocked by undocumented/unpassed gate: '+gate)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fingerprint', action='store_true', help='Print source fingerprint without approving a release.')
    parser.add_argument('--report', help='Reviewed JSON hardware/CI evidence for stable promotion.')
    args = parser.parse_args()
    source = fingerprint()
    if args.fingerprint: print(source); return
    version = (ROOT/'VERSION').read_text().strip()
    if re.fullmatch(r'\d+\.\d+\.\d+-rc[1-9]\d*', version):
        print('Candidate only: hardware validation remains required.'); return
    if not re.fullmatch(r'\d+\.\d+\.\d+', version): raise ValueError('Invalid version')
    if not args.report: raise ValueError('Stable publishing requires --report with all release gates passed')
    validate(json.loads(Path(args.report).read_text()), version, source)
    print('Stable evidence gate PASS (reviewed assertions; CI cannot perform hardware tests)')


if __name__ == '__main__':
    try: main()
    except (ValueError, OSError) as exc: raise SystemExit(str(exc)) from exc
