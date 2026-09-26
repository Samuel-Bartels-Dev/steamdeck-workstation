#!/usr/bin/env python3
"""Regression for the Python 3.13 installer preflight failure."""
import hashlib
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
renderer=runpy.run_path(str(ROOT/'tools/render-command-docs.py'))

class Parser:
    def __init__(self,text): self.text=text
    def format_help(self): return self.text

class ManualCompatibility(unittest.TestCase):
    def test_python_usage_wrap_variants_produce_identical_manual_text(self):
        body='NAME\n  A command\n\nDESCRIPTION\n  Real behavior.\n'
        old='usage: deckctl [-h]\n               {detect,apply}\n               ...\n\n'+body
        new='usage: deckctl [-h]\n               {detect,apply} ...\n\n'+body
        self.assertEqual(renderer['manual_help'](Parser(old)),renderer['manual_help'](Parser(new)))
    def test_long_option_and_choice_stay_together_semantically(self):
        old='usage: deckctl game register --storage-role\n   {internal,pc_games,emulation}\n   name\n\nDESCRIPTION\n  Register.\n'
        new='usage: deckctl game register\n   --storage-role {internal,pc_games,emulation} name\n\nDESCRIPTION\n  Register.\n'
        text=renderer['manual_help'](Parser(new))
        self.assertEqual(renderer['manual_help'](Parser(old)),text)
        self.assertIn('--storage-role',text)
        self.assertIn('{internal,pc_games,emulation}',text)
    def test_body_and_real_argument_changes_are_not_hidden(self):
        first=renderer['manual_help'](Parser('usage: deckctl --old\n\nDESCRIPTION\n  Original.'))
        argument=renderer['manual_help'](Parser('usage: deckctl --new\n\nDESCRIPTION\n  Original.'))
        body=renderer['manual_help'](Parser('usage: deckctl --old\n\nDESCRIPTION\n  Changed.'))
        self.assertNotEqual(first,argument)
        self.assertNotEqual(first,body)
    def test_check_rejects_stale_document(self):
        main=renderer['main']
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'manual.md';path.write_text('stale')
            with patch.dict(main.__globals__,{'documents':lambda:{path:'current'}}),patch.object(sys,'argv',['render-command-docs.py','--check']):
                with self.assertRaisesRegex(SystemExit,'Out-of-date manual'):main()
                self.assertEqual(path.read_text(),'stale')
                path.write_text('current');self.assertEqual(main(),0)
    def test_v0220_preserved_except_explicit_maintenance_changes(self):
        guard=json.loads((ROOT/'tests/fixtures/baseline-v0.2.20.json').read_text())
        changed=set()
        for name,sha in guard['files'].items():
            path=ROOT/name;self.assertTrue(path.is_file(),name)
            if hashlib.sha256(path.read_bytes()).hexdigest()!=sha:changed.add(name)
        patch_changes=set(json.loads((ROOT/'tests/fixtures/baseline-v0.2.21.json').read_text())['provisioning_changes'])
        patch_changes.update(json.loads((ROOT/'tests/fixtures/baseline-v0.2.22.json').read_text())['maintenance_changes'])
        patch_changes.update(json.loads((ROOT/'tests/fixtures/baseline-v0.2.23.json').read_text())['maintenance_changes'])
        patch_changes.update(json.loads((ROOT/'tests/fixtures/baseline-v0.2.24.json').read_text())['plugin_changes'])
        patch_changes.update(json.loads((ROOT/'tests/fixtures/baseline-v0.2.25.json').read_text())['reliability_changes'])
        self.assertEqual(changed-patch_changes,set(guard['maintenance_changes'])-patch_changes)
        self.assertRegex((ROOT/'VERSION').read_text().strip(),r'^0\.2\.44(?:-rc[1-9]\d*)?$')

if __name__=='__main__':unittest.main(verbosity=2)
