#!/usr/bin/env python3
"""Preflight isolation and upgrades on an already-provisioned home directory."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'lib'))
from deckctl import core

class ExistingInstallation(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.home=Path(temp.name)/'home';self.home.mkdir()
        self.fakebin=Path(temp.name)/'bin';self.fakebin.mkdir()
        self.env={**os.environ,'HOME':str(self.home),
                  'DECKCTL_CONFIG':str(self.home/'live-config'),
                  'DECKCTL_STATE':str(self.home/'live-state'),
                  'XDG_CONFIG_HOME':str(self.home/'live-xdg-config'),
                  'XDG_DATA_HOME':str(self.home/'live-xdg-data'),
                  'XDG_STATE_HOME':str(self.home/'live-xdg-state'),
                  'XDG_CACHE_HOME':str(self.home/'live-xdg-cache'),
                  'PATH':str(self.fakebin)+':'+os.environ['PATH'],
                  'PYTHONDONTWRITEBYTECODE':'1'}
        self.marker=self.home/'systemctl-called'
        self.systemctl('enabled',0)

    def systemctl(self,output,code):
        p=self.fakebin/'systemctl'
        p.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$HOME/systemctl-called"\nprintf "%s\\n" "'+output+'"\nexit '+str(code)+'\n')
        p.chmod(0o755)

    def run_tool(self,*args):
        result=subprocess.run([sys.executable,str(ROOT/'tools/install-control-plane'),*map(str,args)],env=self.env,capture_output=True,text=True,timeout=45)
        self.assertEqual(result.returncode,0,result.stderr)
        return Path(result.stdout.strip())

    def test_preflight_guardrails_isolated_from_enabled_host_and_live_paths(self):
        for key in ('DECKCTL_CONFIG','DECKCTL_STATE','XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_STATE_HOME','XDG_CACHE_HOME'):
            p=Path(self.env[key]);p.mkdir();(p/'preserve').write_bytes(b'pre-existing setting')
        before={str(p.relative_to(self.home)):p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        result=subprocess.run([sys.executable,str(ROOT/'tests/contract/test_regressions.py')],env=self.env,capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertFalse(self.marker.exists(),'Presentation fixture queried the live host service')
        after={str(p.relative_to(self.home)):p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
        self.assertEqual(before,after)

    def test_real_detector_still_recognizes_enabled_service(self):
        with patch.dict(os.environ,self.env):self.assertTrue(core._decky_loader_present())
        self.assertEqual(self.marker.read_text().strip(),'is-enabled plugin_loader.service')

    def test_real_detector_rejects_disabled_failed_or_unrecognized_service(self):
        for text,rc in [('disabled',1),('enabled',1),('unknown output',0)]:
            self.systemctl(text,rc)
            with self.subTest(output=text,rc=rc),patch.dict(os.environ,self.env):
                self.assertFalse(core._decky_loader_present())

    def test_real_detector_uses_installed_executable_without_service_query(self):
        p=self.home/'homebrew/services/PluginLoader';p.parent.mkdir(parents=True)
        p.write_text('#!/bin/sh\nexit 0\n');p.chmod(0o755)
        with patch.dict(os.environ,self.env):self.assertTrue(core._decky_loader_present())
        self.assertFalse(self.marker.exists())

    def test_upgrade_and_repeat_preserve_prior_release_and_user_payloads(self):
        # Use a complete versioned control-plane tree to exercise promotion of an
        # existing installation, not just creation of an empty current symlink.
        old_source=self.home.parent/'previous-source'
        shutil.copytree(ROOT,old_source,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.git','release'))
        (old_source/'VERSION').write_text('0.2.22\n')
        old=self.run_tool(old_source)
        (old/'README.md').write_text('Previous installed release with local notes\n')
        old_inventory={str(p.relative_to(old)):hashlib.sha256(p.read_bytes()).hexdigest() for p in old.rglob('*') if p.is_file()}
        payloads={
            '.config/deckctl/settings.json':b'{"profile":"oled","custom":"keep"}',
            '.config/deckctl/decky-selection.json':b'{"selected":["SDH-CssLoader"]}',
            '.config/deckctl/css-profiles/custom/manifest.json':b'{"name":"custom recovery"}',
            '.local/state/deckctl/setup.json':b'{"android":"complete"}',
            'Android_Waydroid/waydroid.img':b'keep Android image',
            '.local/share/waydroid/data/keep.dat':b'keep Android app data',
            'homebrew/themes/Round/config_USER.json':b'{"active":true}',
            'homebrew/plugins/SDH-CssLoader/plugin.json':b'{"name":"CSS Loader"}',
            '.local/share/Steam/userdata/123/config/shortcuts.vdf':b'keep shortcuts',
            '.local/share/Steam/userdata/123/config/grid/123.png':b'keep artwork',
            '.config/starship.toml':b'keep terminal customization',
        }
        for name,content in payloads.items():
            p=self.home/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)
        bashrc=self.home/'.bashrc';bashrc.write_text(bashrc.read_text()+'\n# personal shell config\n')
        for attempt in range(2):
            with self.subTest(attempt=attempt):
                installed=self.run_tool(ROOT)
                current=self.home/'.local/share/steamdeck-workstation/current'
                self.assertEqual(current.resolve(),installed)
                self.assertEqual(installed.name,'0.2.43')
                result=subprocess.run([str(self.home/'.local/bin/deckctl'),'--version'],env=self.env,capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout.strip(),'0.2.43')
                for name,content in payloads.items():self.assertEqual((self.home/name).read_bytes(),content,name)
                self.assertEqual(old_inventory,{str(p.relative_to(old)):hashlib.sha256(p.read_bytes()).hexdigest() for p in old.rglob('*') if p.is_file()})
                self.assertIn('# personal shell config',bashrc.read_text())
                self.assertEqual(bashrc.read_text().count('# >>> steamdeck-workstation deckctl >>>'),1)
                self.assertTrue((self.home/'.local/share/man/man1/deckctl.1').is_file())

    def test_maintenance_preserves_all_runtime_modules(self):
        guard=json.loads((ROOT/'tests/fixtures/baseline-v0.2.22.json').read_text())
        changed=set()
        for name,expected in guard['files'].items():
            p=ROOT/name;self.assertTrue(p.is_file(),name)
            self.assertEqual(p.stat().st_mode & 0o777,expected['mode'],name)
            if hashlib.sha256(p.read_bytes()).hexdigest()!=expected['sha256']:changed.add(name)
        maintenance=set(json.loads((ROOT/'tests/fixtures/baseline-v0.2.23.json').read_text())['maintenance_changes'])
        maintenance.update(json.loads((ROOT/'tests/fixtures/baseline-v0.2.24.json').read_text())['plugin_changes'])
        maintenance.update(json.loads((ROOT/'tests/fixtures/baseline-v0.2.25.json').read_text())['reliability_changes'])
        self.assertEqual(changed-maintenance,set(guard['maintenance_changes'])-maintenance)
        for name in ('lib/deckctl/android.py','modules/decky/css-stack.json','tools/install-control-plane'):
            self.assertNotIn(name,changed)



class Cleanup(unittest.TestCase):
    def setUp(self):
        from deckctl import setup_cleanup
        self.cleanup=setup_cleanup
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.home=Path(temp.name)
        for patcher in (patch.dict(os.environ,{'HOME':str(self.home)}),
                        patch.object(core,'STATE',self.home/'state'),
                        patch.object(setup_cleanup.desktop,'desktop_dir',return_value=self.home/'Desktop')):
            patcher.start();self.addCleanup(patcher.stop)
        self.stage=self.home/'Desktop/Deck-Setup-Staged';self.stage.mkdir(parents=True)

    def ready(self):
        app=self.home/'Applications/EmuDeck.AppImage';app.parent.mkdir();app.write_text('fixture');app.chmod(0o755)
        config=self.home/'.config/EmuDeck';config.mkdir(parents=True)
        (config/'.finished').touch();(config/'.ui-finished').touch()

    def test_emulation_directory_alone_and_running_install_are_not_ready(self):
        (self.home/'Emulation').mkdir()
        self.assertFalse(self.cleanup.emudeck_ready())
        self.ready();self.assertTrue(self.cleanup.emudeck_ready())
        (self.home/'.config/EmuDeck/install.pid').write_text('123')
        self.assertFalse(self.cleanup.emudeck_ready())

    def test_legacy_downloader_removed_only_after_vendor_completion(self):
        for folder in (self.stage,self.home/'Desktop'):
            (folder/'EmuDeck.desktop').write_text(self.cleanup.LEGACY_EMUDECK)
        self.assertEqual(self.cleanup.cleanup(),0)
        self.assertTrue((self.stage/'EmuDeck.desktop').exists())
        self.ready();self.assertEqual(self.cleanup.cleanup(),0)
        self.assertFalse((self.stage/'EmuDeck.desktop').exists())
        self.assertFalse((self.home/'Desktop/EmuDeck.desktop').exists())
        self.assertTrue((self.home/'Applications/EmuDeck.AppImage').exists())

    def test_dry_run_preserves_files_and_does_not_create_state(self):
        self.ready();p=self.stage/'EmuDeck.desktop';p.write_text(self.cleanup.LEGACY_EMUDECK)
        self.assertEqual(self.cleanup.cleanup(True),0)
        self.assertTrue(p.exists());self.assertFalse(core.STATE.exists())

    def test_receipt_cleanup_preserves_modified_apps_archives_and_unrelated_files(self):
        self.ready();p=self.stage/'EmuDeck.desktop';p.write_text('downloaded installer')
        (self.stage/'README-EMUDECK.txt').write_text('staged instructions')
        self.cleanup.record('emudeck')
        app=self.home/'Desktop/EmuDeck.desktop';app.write_text('[Desktop Entry]\nExec=/home/deck/Applications/EmuDeck.AppImage\n')
        custom=self.stage/'personal.zip';custom.write_bytes(b'keep')
        self.cleanup.cleanup()
        self.assertFalse(p.exists());self.assertFalse((self.stage/'README-EMUDECK.txt').exists())
        self.assertTrue(app.exists());self.assertEqual(custom.read_bytes(),b'keep')
        p.write_text('modified user installer')
        self.cleanup.cleanup();self.assertTrue(p.exists())

    def test_symlink_installer_and_parent_are_never_followed(self):
        self.ready();outside=self.home/'keep.desktop';outside.write_text(self.cleanup.LEGACY_EMUDECK)
        link=self.stage/'EmuDeck.desktop';link.symlink_to(outside)
        self.cleanup.cleanup();self.assertTrue(link.is_symlink());self.assertTrue(outside.exists())
        link.unlink();self.stage.rmdir()
        folder=self.home/'outside';folder.mkdir();(folder/'EmuDeck.desktop').write_text(self.cleanup.LEGACY_EMUDECK)
        self.stage.symlink_to(folder,target_is_directory=True)
        self.cleanup.cleanup();self.assertTrue((folder/'EmuDeck.desktop').exists())

    def test_failed_detection_preserves_tracked_installer(self):
        p=self.stage/'decky_installer.desktop';p.write_text('tracked')
        self.cleanup.record('decky')
        with patch.object(core,'_decky_loader_present',return_value=False):self.cleanup.cleanup()
        self.assertTrue(p.exists())
        with patch.object(core,'_decky_loader_present',return_value=True):self.cleanup.cleanup()
        self.assertFalse(p.exists())

    def test_verified_emudeck_staging_skips_downloader(self):
        self.ready()
        env={**os.environ,'DECKCTL_ROOT':str(ROOT)}
        result=subprocess.run(['bash',str(ROOT/'modules/emulation/install.sh')],env=env,capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse((self.stage/'EmuDeck.desktop').exists())

    def test_verified_emudeck_without_progress_receipt_is_not_relaunched(self):
        self.ready()
        step={'id':'emudeck','title':'EmuDeck','detect':self.cleanup.emudeck_ready,'launch':lambda:self.fail('relaunch'),'description':'fixture'}
        with patch.object(core,'setup_steps',return_value=[step]),patch.object(core,'create_setup_shortcut',return_value=self.home/'Continue.desktop'),patch.object(core,'verify'),patch('builtins.input',side_effect=AssertionError('Unexpected prompt')):
            self.assertEqual(core.setup_run(),0)
        self.assertIn('emudeck',core.setup_state()['completed'])

    def test_update_download_cleanup_is_confined_and_hash_checked(self):
        from deckctl import reliability
        folder=core.STATE/'downloads';folder.mkdir(parents=True)
        arc=folder/'release.tar.gz';arc.write_bytes(b'downloaded')
        outside=self.home/'user-release.zip';outside.write_bytes(b'downloaded')
        sha=hashlib.sha256(b'downloaded').hexdigest()
        reliability._cleanup_update_download(outside,sha);self.assertTrue(outside.exists())
        reliability._cleanup_update_download(arc,'wrong-hash');self.assertTrue(arc.exists())
        arc.unlink();arc.symlink_to(outside)
        reliability._cleanup_update_download(arc,sha);self.assertTrue(arc.is_symlink())
        arc.unlink();arc.write_bytes(b'downloaded')
        reliability._cleanup_update_download(arc,sha);self.assertFalse(arc.exists())
        self.assertTrue(outside.exists())

    def test_update_removes_only_automatic_download_after_success(self):
        from deckctl import reliability
        folder=core.STATE/'downloads';folder.mkdir(parents=True)
        arc=folder/'release.tar.gz'
        installed=self.home/'installed';installed.mkdir();(installed/'VERSION').write_text('0.2.32')
        current=self.home/'current';current.symlink_to(installed)
        for explicit,validation_status,removed in [(False,0,True),(True,0,False),(False,1,False)]:
            arc.write_bytes(b'archive fixture')
            results=[subprocess.CompletedProcess([],validation_status)]
            if not validation_status:results.append(subprocess.CompletedProcess([],0,str(installed)+'\n',''))
            with self.subTest(explicit=explicit,validation_status=validation_status),patch.object(reliability,'CURRENT_LINK',current),patch.object(reliability,'_download_release_archive',return_value=arc),patch.object(reliability,'_extract_release',return_value=self.home/'extracted'),patch.object(reliability.subprocess,'run',side_effect=results),patch.object(reliability,'_history_append'),patch('deckctl.upgrade_plan.show'):
                self.assertEqual(reliability.update_apply(str(arc) if explicit else None),validation_status)
            self.assertEqual(arc.exists(),not removed)
            self.assertTrue((installed/'VERSION').exists())

if __name__=='__main__':unittest.main(verbosity=2)
