#!/usr/bin/env python3
"""Exercise the installer's actual preflight statements without vendor execution."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]

class InstallerPermissions(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.work=Path(tmp.name)
        self.repo=self.work/'repo'
        shutil.copytree(ROOT,self.repo,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.git','release'))
        script=(ROOT/'install.sh').read_text()
        # Root refusal is unchanged; this fixture executes only the preflight
        # statements, never install-control-plane, module actions or vendor code.
        self.prefix=script[script.index('command -v python3'):script.index('if [[ "${DECKCTL_REEXEC')]
        fake=self.repo/'bin/deckctl'
        fake.write_text('''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
assert sys.argv[1:] == ['repo','validate']
root=Path.cwd()
expected=json.loads(Path(os.environ['MODE_FIXTURE']).read_text())
actual={str(p.relative_to(root)):p.stat().st_mode & 0o777 for p in root.rglob('*') if p.is_file()}
if actual != expected:
    print('Fixture rejected permission mutation')
    raise SystemExit(7)
print('Fixture modes preserved')
''')
        self.expected=self.inventory()
        modes={name:entry[1] for name,entry in self.expected.items()}
        self.fixture=self.work/'modes.json';self.fixture.write_text(json.dumps(modes))

    def inventory(self):
        return {str(p.relative_to(self.repo)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mode & 0o777) for p in self.repo.rglob('*') if p.is_file()}

    def run_prefix(self,prefix):
        return subprocess.run(['bash','-c','set -euo pipefail\n'+prefix+'\nprintf "PREFLIGHT_RETURNED\\n"\n'],cwd=self.repo,env={**os.environ,'MODE_FIXTURE':str(self.fixture)},capture_output=True,text=True,timeout=10)

    def test_actual_preflight_preserves_all_file_contents_and_modes(self):
        self.assertEqual((self.repo/'modules/terminal/terminal.sh').stat().st_mode & 0o777,0o644)
        result=self.run_prefix(self.prefix)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('PREFLIGHT_RETURNED',result.stdout)
        self.assertEqual(self.expected,self.inventory())

    def test_old_blanket_chmod_reproduces_reported_failure(self):
        result=self.run_prefix('chmod +x bin/deckctl modules/*/*.sh tools/* 2>/dev/null || true\n'+self.prefix)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual((self.repo/'modules/terminal/terminal.sh').stat().st_mode & 0o777,0o755)
        self.assertIn('Pre-install checks failed',result.stderr)
        self.assertNotIn('PREFLIGHT_RETURNED',result.stdout)

    def test_real_validation_failure_still_blocks_provisioning(self):
        (self.repo/'bin/deckctl').write_text('#!/bin/sh\nexit 9\n')
        result=self.run_prefix(self.prefix)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Pre-install checks failed',result.stderr)
        self.assertNotIn('PREFLIGHT_RETURNED',result.stdout)

    def test_previous_runtime_and_package_permissions_remain_preserved(self):
        guard=json.loads((ROOT/'tests/fixtures/baseline-v0.2.23.json').read_text())
        changed=set()
        for name,entry in guard['files'].items():
            p=ROOT/name;self.assertTrue(p.is_file(),name)
            self.assertEqual(p.stat().st_mode & 0o777,entry['mode'],name)
            if hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:changed.add(name)
        delegated=set(json.loads((ROOT/'tests/fixtures/baseline-v0.2.24.json').read_text())['plugin_changes'])
        delegated.update(json.loads((ROOT/'tests/fixtures/baseline-v0.2.25.json').read_text())['reliability_changes'])
        changed-=delegated
        self.assertEqual(changed,set(guard['maintenance_changes'])-delegated)
        self.assertFalse(any(n.startswith('modules/') for n in changed))
        self.assertFalse(any(n.startswith('lib/') and n!='lib/deckctl/helptext.py' for n in changed))

if __name__=='__main__':unittest.main(verbosity=2)
