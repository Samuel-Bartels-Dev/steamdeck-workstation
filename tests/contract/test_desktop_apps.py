#!/usr/bin/env python3
"""Exercise module scripts with isolated Flatpak state; no network or vendor apps."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
APPS = {'utilities': ['com.github.tchx84.Flatseal', 'app.zen_browser.zen'],
        'dev': ['com.visualstudio.code', 'dev.zed.Zed'],
        'media': ['org.videolan.VLC', 'tv.plex.PlexDesktop', 'com.spotify.Client']}


class DesktopApps(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.root = self.home / 'repo'
        self.bin = self.home / 'bin'
        self.bin.mkdir()
        (self.root / 'lib/deckctl').mkdir(parents=True)
        shutil.copy2(ROOT / 'lib/deckctl/module.sh', self.root / 'lib/deckctl/module.sh')
        (self.root / 'lib/deckctl/__init__.py').write_text('')
        (self.root / 'lib/deckctl/desktop.py').write_text('def apply(): return 0\n')
        for module in APPS:
            shutil.copytree(ROOT / 'modules' / module, self.root / 'modules' / module)
        (self.root / 'modules/dev/install-codex.sh').write_text('#!/bin/bash\nexit 0\n')
        self.state = self.home / 'flatpak-state.json'
        self.calls = self.home / 'flatpak-calls.jsonl'
        self.state.write_text('[]')
        stub = self.bin / 'flatpak'
        stub.write_text(f'''#!{sys.executable}
import json,os,sys
from pathlib import Path
state=Path(os.environ['FAKE_FLATPAK_STATE'])
apps=json.loads(state.read_text())
args=sys.argv[1:]
if args[0]=='info': sys.exit(0 if args[1] in apps else 1)
assert args[:5]==['install','--user','-y','flathub',args[-1]],args
with open(os.environ['FAKE_FLATPAK_CALLS'],'a') as f: f.write(json.dumps(args)+'\\n')
if args[-1]==os.environ.get('FAIL_APP'): sys.exit(1)
apps.append(args[-1]);state.write_text(json.dumps(apps))
''')
        stub.chmod(0o755)
        for name, output in [('codex', 'Logged in'), ('distrobox', 'deck-dev'), ('podman', 'podman')]:
            path = self.bin / name
            path.write_text('#!/bin/sh\nprintf "%s\\n" "' + output + '"\n')
            path.chmod(0o755)
        self.env = {**os.environ, 'HOME': str(self.home), 'DECKCTL_ROOT': str(self.root),
                    'DECKCTL_CONFIG': str(self.home / 'config'), 'DECKCTL_STATE': str(self.home / 'state'),
                    'PATH': str(self.bin) + ':/usr/bin:/bin',
                    'FAKE_FLATPAK_STATE': str(self.state), 'FAKE_FLATPAK_CALLS': str(self.calls)}

    def run_module(self, module, action, **env):
        return subprocess.run(['bash', str(self.root / 'modules' / module / (action + '.sh'))],
                              env={**self.env, **env}, capture_output=True, text=True, timeout=15)

    def test_install_and_repeat_skip_existing_apps(self):
        for module, apps in APPS.items():
            with self.subTest(module=module):
                self.state.write_text(json.dumps(apps[:1]))
                self.calls.write_text('')
                result = self.run_module(module, 'install')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(set(json.loads(self.state.read_text())), set(apps))
                calls = self.calls.read_text()
                self.assertEqual([json.loads(line)[-1] for line in calls.splitlines()], apps[1:])
                self.assertEqual(self.run_module(module, 'install').returncode, 0)
                self.assertEqual(self.calls.read_text(), calls)

    def test_failed_download_is_retryable_and_other_apps_are_attempted(self):
        self.state.write_text('[]')
        result = self.run_module('media', 'install', FAIL_APP='org.videolan.VLC')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(set(json.loads(self.state.read_text())), {'tv.plex.PlexDesktop', 'com.spotify.Client'})
        report = json.loads(self.run_module('media', 'verify').stdout)
        self.assertEqual(report['status'], 'NOT_INSTALLED')
        self.assertIn('VLC', report['message'])
        self.assertEqual(self.run_module('media', 'install').returncode, 0)
        self.assertEqual(set(json.loads(self.state.read_text())), set(APPS['media']))

    def test_verify_reports_each_missing_app_without_mutating_state(self):
        for module, apps in APPS.items():
            for missing in apps:
                with self.subTest(module=module, missing=missing):
                    self.state.write_text(json.dumps([app for app in apps if app != missing]))
                    before = self.state.read_bytes()
                    result = self.run_module(module, 'verify')
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(json.loads(result.stdout)['status'], 'NOT_INSTALLED')
                    self.assertEqual(self.state.read_bytes(), before)
                    self.assertFalse(self.calls.exists())
            self.state.write_text(json.dumps(apps))
            self.assertEqual(json.loads(self.run_module(module, 'verify').stdout)['status'], 'READY')


if __name__ == '__main__':
    unittest.main(verbosity=2)
