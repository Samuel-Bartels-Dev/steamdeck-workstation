#!/usr/bin/env python3
"""Requested Store identities and repeatable upgrades of saved Decky selections."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'lib'))
from deckctl import core, decky_installer as installer

REQUESTED={'SDH-GameThemeMusic':'Game Theme Music','ControllerTools':'Controller Tools',
           'MagicPodsDecky':'MagicPods','Bluetooth':'Bluetooth','TabMaster':'TabMaster'}

class SelectionUpgrade(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.home=Path(tmp.name)
        self.selection=self.home/'config/decky-selection.json'
        self.plugins=self.home/'homebrew/plugins'
        for target,attr,value in [(core,'_decky_selection_path',lambda:self.selection),
                                  (Path,'home',lambda:self.home),
                                  (installer,'PLUGIN_ROOT',self.plugins),
                                  (installer,'BACKUP_ROOT',self.home/'backups'),
                                  (installer,'RECEIPTS',self.home/'receipts.json')]:
            p=patch.object(target,attr,value);p.start();self.addCleanup(p.stop)
        p=patch.object(core,'_decky_loader_present',return_value=True);p.start();self.addCleanup(p.stop)
        p=patch.object(installer,'_restart_decky',return_value=True);self.restart=p.start();self.addCleanup(p.stop)
        p=patch('sys.stdout',new=io.StringIO());p.start();self.addCleanup(p.stop)

    def save_old(self,revision=4,selected=None):
        self.selection.parent.mkdir(parents=True,exist_ok=True)
        data={'schema_version':1,'manifest_schema_version':revision,
              'selected_folders':selected if selected is not None else ['moondeck','custom-plugin'],
              'personal_note':'retain me'}
        self.selection.write_text(json.dumps(data));return self.selection.read_bytes()

    def test_official_identities_defaults_and_policy_are_consistent(self):
        items=core._decky_item_map()
        policies=json.loads((ROOT/'modules/decky/plugin-policies.json').read_text())['plugins']
        for folder,name in REQUESTED.items():
            self.assertEqual(items[folder]['name'],name)
            self.assertIn(folder,core._decky_default_selection())
            self.assertEqual(policies[name]['mode'],'install-only')
        all_items=[x['folder'] for category in ('core','recommended','optional','avoid_by_default') for x in core._decky_manifest().get(category,[])]
        self.assertEqual(len(all_items),len(set(all_items)))

    def test_read_only_upgrade_preserves_other_choices(self):
        before=self.save_old()
        self.assertEqual(core._decky_selected_folders(),set(REQUESTED)|{'moondeck','custom-plugin'})
        self.assertEqual(self.selection.read_bytes(),before)

    def test_commit_preserves_metadata_and_is_repeatable(self):
        self.save_old();core._decky_upgrade_selection()
        data=json.loads(self.selection.read_text())
        self.assertEqual(data['personal_note'],'retain me')
        self.assertEqual(set(data['selected_folders']),set(REQUESTED)|{'moondeck','custom-plugin'})
        before=self.selection.read_bytes();core._decky_upgrade_selection()
        self.assertEqual(self.selection.read_bytes(),before)

    def test_explicit_opt_out_survives_further_installs(self):
        self.save_old();core._decky_write_selection({'moondeck','Bluetooth'})
        core._decky_upgrade_selection()
        self.assertEqual(core._decky_selected_folders(),{'moondeck','Bluetooth'})

    def test_legacy_selection_without_revision_gains_requests(self):
        self.save_old();data=json.loads(self.selection.read_text());data.pop('manifest_schema_version')
        self.selection.write_text(json.dumps(data))
        self.assertTrue(set(REQUESTED)<=core._decky_selected_folders())

    def test_dry_run_and_cancel_leave_selection_and_store_untouched(self):
        before=self.save_old()
        with patch.object(installer,'_store_catalog') as store,patch('builtins.input',return_value='n'):
            self.assertEqual(installer.install_selected(dry_run=True),0)
            self.assertEqual(installer.install_selected(),0)
            store.assert_not_called()
        self.assertEqual(self.selection.read_bytes(),before)
        self.assertFalse(self.plugins.exists())

    def test_missing_loader_never_commits(self):
        before=self.save_old()
        with patch.object(core,'_decky_loader_present',return_value=False):
            self.assertEqual(installer.install_selected(assume_yes=True),2)
        self.assertEqual(self.selection.read_bytes(),before)

    def test_store_error_remains_retryable_without_success_receipts(self):
        self.save_old(selected=[])
        with patch.object(installer,'_store_catalog',side_effect=OSError('offline')):
            self.assertEqual(installer.install_selected(assume_yes=True),3)
        self.assertEqual(core._decky_selected_folders(),set(REQUESTED))
        self.assertFalse(installer.RECEIPTS.exists())

    def test_real_zip_install_existing_state_and_second_run_no_downloads(self):
        self.save_old(selected=[])
        self.plugins.mkdir(parents=True)
        untouched=self.home/'homebrew/settings/TabMaster.json';untouched.parent.mkdir(parents=True)
        untouched.write_bytes(b'{"tabs":["My Games"]}')
        catalog=[{'name':name,'versions':[{'name':'test-version','hash':folder}]} for folder,name in REQUESTED.items()]
        def download(url,dest):
            folder=dest.stem
            with zipfile.ZipFile(dest,'w') as z:
                z.writestr(folder+'/plugin.json',json.dumps({'name':REQUESTED[folder],'author':'fixture'}))
                z.writestr(folder+'/package.json','{"version":"1.0.0"}')
                z.writestr(folder+'/dist/index.js','export default {};')
        with patch.object(installer,'_store_catalog',return_value=catalog) as store,patch.object(installer,'_download',side_effect=download) as fetch:
            self.assertEqual(installer.install_selected(assume_yes=True),0)
            self.assertEqual(fetch.call_count,5)
            self.assertEqual(installer.install_selected(assume_yes=True),0)
            self.assertEqual(fetch.call_count,5);self.assertEqual(store.call_count,1)
        self.assertEqual(untouched.read_bytes(),b'{"tabs":["My Games"]}')
        installed=core._decky_installed_plugins()
        self.assertTrue(all(installed[f]['valid'] for f in REQUESTED))
        self.assertEqual(set(json.loads(installer.RECEIPTS.read_text())),set(REQUESTED))
        self.restart.assert_called_once()

    def test_previous_release_preserved_except_reviewed_changes(self):
        guard=json.loads((ROOT/'tests/fixtures/baseline-v0.2.24.json').read_text())
        changed=set()
        for name,entry in guard['files'].items():
            p=ROOT/name;self.assertTrue(p.is_file(),name)
            self.assertEqual(p.stat().st_mode & 0o777,entry['mode'],name)
            if hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']:changed.add(name)
        delegated=set(json.loads((ROOT/'tests/fixtures/baseline-v0.2.25.json').read_text())['reliability_changes'])
        changed-=delegated
        self.assertEqual(changed,set(guard['plugin_changes'])-delegated)
        for name in ['lib/deckctl/android.py','lib/deckctl/css_stack.py','modules/decky/css-stack.json',
                     'lib/deckctl/setup_cleanup.py','lib/deckctl/reliability.py','install.sh','tools/install-control-plane']:
            self.assertNotIn(name,changed)

if __name__=='__main__':unittest.main(verbosity=2)
