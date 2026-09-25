#!/usr/bin/env python3
"""Offline stateful upgrade, resume, restore, migration and distribution contracts."""
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'lib'))
from deckctl import core, provisioning, file_state, lifecycle, storage_ops, shortcut_ops, upgrade_plan, reliability

class Fixture(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.home=Path(tmp.name)
        for target,name,value in [(Path,'home',lambda:self.home),(core,'STATE',self.home/'state'),
                                  (core,'CONFIG_HOME',self.home/'config')]:
            p=patch.object(target,name,value);p.start();self.addCleanup(p.stop)
        p=patch.dict(os.environ,{'HOME':str(self.home)});p.start();self.addCleanup(p.stop)
        p=patch('sys.stdout',new=io.StringIO());p.start();self.addCleanup(p.stop)
    def write(self,path,data='payload'):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(data);return path

class Setup(Fixture):
    def steps(self,detect,launch,sid='android',auto=True):
        return [{'id':sid,'title':sid,'description':'fixture','detect':detect,'launch':launch,'noninteractive':auto}]
    def run_setup(self,steps,**kwargs):
        with patch.object(core,'setup_steps',return_value=steps),patch.object(core,'create_setup_shortcut'),patch('deckctl.setup_cleanup.cleanup'):
            return provisioning.run(**kwargs)
    def test_fresh_install_then_repeat_skips_verified_step(self):
        marker=self.home/'android-state';calls=[]
        def launch():calls.append(True);marker.write_text('initialized');return True
        steps=self.steps(marker.exists,launch)
        self.assertEqual(self.run_setup(steps),0);self.assertEqual(self.run_setup(steps),0)
        self.assertEqual(len(calls),1)
    def test_interrupted_state_retries_and_verifies(self):
        marker=self.home/'state-created'
        state={'completed':[],'skipped':[]};provisioning.record(state,'android','RUNNING')
        with patch.object(core,'setup_steps',return_value=self.steps(marker.exists,lambda:True)):
            self.assertEqual(provisioning.rows()[0]['status'],'INTERRUPTED')
        self.assertEqual(self.run_setup(self.steps(marker.exists,lambda:(marker.write_text('ok') or True))),0)
    def test_download_failure_remains_failed_and_retry_succeeds(self):
        marker=self.home/'installed'
        steps=self.steps(marker.exists,lambda:False)
        self.assertEqual(self.run_setup(steps),2)
        self.assertEqual(core.setup_state()['steps']['android']['status'],'FAILED')
        steps[0]['launch']=lambda:(marker.write_text('ready') or True)
        self.assertEqual(self.run_setup(steps),0)
    def test_manual_mark_cannot_fake_missing_component(self):
        with patch('builtins.input',return_value='m'):
            self.assertEqual(self.run_setup(self.steps(lambda:False,lambda:True,auto=False)),2)
        self.assertNotIn('android',core.setup_state()['completed'])
    def test_account_presence_requires_confirmation(self):
        steps=self.steps(lambda:True,lambda:True,'moonlight',False)
        with patch.object(core,'setup_steps',return_value=steps):self.assertEqual(provisioning.rows()[0]['status'],'CONFIG_REQUIRED')
        with patch('builtins.input',side_effect=['y','']):self.assertEqual(self.run_setup(steps),0)
        self.assertEqual(core.setup_state()['steps']['moonlight']['status'],'CONFIRMED')
    def test_named_retry_does_not_run_other_failed_step(self):
        marker=self.home/'fixed'
        steps=self.steps(marker.exists,lambda:(marker.write_text('ok') or True))
        steps+=self.steps(lambda:False,lambda:self.fail('unrelated launch'),'media')
        self.assertEqual(self.run_setup(steps,step_id='android'),2)
        self.assertTrue(marker.exists())
    def test_report_read_only_and_detector_errors_are_visible(self):
        def fail():raise OSError('detector failed')
        before=list(self.home.rglob('*'))
        with patch.object(core,'setup_steps',return_value=self.steps(fail,lambda:False)):
            self.assertEqual(provisioning.report(True),2)
        self.assertEqual(list(self.home.rglob('*')),before)
    def test_apply_retry_skips_only_verified_same_release(self):
        installed=False;calls=[]
        def action(*args,**kwargs):
            nonlocal installed
            calls.append(args);installed=True;return subprocess.CompletedProcess([],0)
        def status(*args):return {'status':'READY' if installed else 'NOT_INSTALLED'}
        with patch.object(core,'enabled_modules',return_value=['base']),patch.object(core,'topo',side_effect=lambda x:x),patch.object(core,'run_action',side_effect=action),patch.object(core,'module_status',side_effect=status),patch.object(core,'create_setup_shortcut'),patch('deckctl.setup_cleanup.cleanup'):
            self.assertEqual(core.apply(),0);self.assertEqual(core.apply(),0);self.assertEqual(len(calls),1)
            installed=False;self.assertEqual(core.apply(),0);self.assertEqual(len(calls),2)
    def test_stale_completed_step_is_repaired(self):
        core.save_setup_state({'completed':['android'],'skipped':[]})
        marker=self.home/'fixed'
        self.assertEqual(self.run_setup(self.steps(marker.exists,lambda:(marker.write_text('ok') or True))),0)

class Restore(Fixture):
    def archive(self):
        source=self.home/'backup-source';self.write(source/'save.dat','backup save')
        dest=self.home/'Emulation/saves';self.write(dest/'save.dat','current save')
        manifest={'format':2,'categories':{'emulation-saves':{'source':str(dest),'arc':'payload/emulation-saves'}}}
        path=self.home/'backup.tar.gz'
        with tarfile.open(path,'w:gz') as tf:
            tf.add(source,arcname='payload/emulation-saves')
            raw=json.dumps(manifest).encode();info=tarfile.TarInfo('deckctl-backup-manifest.json');info.size=len(raw);tf.addfile(info,io.BytesIO(raw))
        return path,dest
    def test_preview_does_not_mutate_user_data(self):
        path,dest=self.archive();before=dest.read_bytes() if dest.is_file() else file_state.inventory(dest)
        with patch.object(lifecycle,'_emu_root',return_value=self.home/'Emulation'):
            self.assertEqual(lifecycle.restore(str(path),dry_run=True),0)
        self.assertEqual(file_state.inventory(dest),before);self.assertFalse(core.STATE.exists())
    def test_restore_verifies_bytes_preserves_extra_files_and_rollback(self):
        path,dest=self.archive();self.write(dest/'other.sav','retain')
        with patch.object(lifecycle,'_emu_root',return_value=self.home/'Emulation'):
            self.assertEqual(lifecycle.restore(str(path),yes=True),0)
        self.assertEqual((dest/'save.dat').read_text(),'backup save');self.assertEqual((dest/'other.sav').read_text(),'retain')
        old=list((core.STATE/'restore-rollback').glob('*/emulation-saves/save.dat'))
        self.assertEqual(old[0].read_text(),'current save')
        result=json.loads(next((core.STATE/'restore-rollback').glob('*/result.json')).read_text())
        self.assertEqual(result['status'],'VERIFIED')
    def test_low_space_rejected_before_user_data_write(self):
        path,dest=self.archive()
        with patch.object(lifecycle,'_emu_root',return_value=self.home/'Emulation'),patch.object(file_state.shutil,'disk_usage',return_value=shutil._ntuple_diskusage(100,100,0)):
            with self.assertRaises(ValueError):lifecycle.restore(str(path),yes=True)
        self.assertEqual((dest/'save.dat').read_text(),'current save');self.assertFalse(core.STATE.exists())
    def test_failure_journal_and_original_retained(self):
        path,dest=self.archive()
        with patch.object(lifecycle,'_emu_root',return_value=self.home/'Emulation'),patch.object(file_state,'atomic_merge',side_effect=OSError('write failure')):
            with self.assertRaises(OSError):lifecycle.restore(str(path),yes=True)
        self.assertEqual((dest/'save.dat').read_text(),'current save')
        result=json.loads(next((core.STATE/'restore-rollback').glob('*/result.json')).read_text());self.assertEqual(result['status'],'FAILED')
    def test_parent_symlink_rejected(self):
        path,dest=self.archive();outside=self.home/'outside';outside.mkdir();shutil.rmtree(dest.parent);dest.parent.symlink_to(outside)
        with patch.object(lifecycle,'_emu_root',return_value=dest.parent):
            with self.assertRaises(ValueError):lifecycle.restore(str(path),yes=True)
    def test_missing_emulation_card_never_falls_back(self):
        (self.home/'Emulation').symlink_to(self.home/'missing-card/Emulation')
        with patch.object(core,'storage_health',return_value=[]):
            with self.assertRaises(ValueError):lifecycle._emu_root()

class Migration(Fixture):
    def tree(self):
        source=self.home/'Emulation';target=self.home/'card/Emulation'
        for root in (source,target):
            self.write(root/'roms/game.rom','rom');self.write(root/'bios/bios.bin','bios');self.write(root/'saves/game.sav','save')
        return source,target
    def test_mismatch_blocks_finalize_preserves_original(self):
        source,target=self.tree();(target/'saves/game.sav').write_text('wrong')
        with patch.object(storage_ops,'_emu_mount',return_value=(target.parent,'DECK-EMU')):self.assertEqual(storage_ops.finalize_emulation(True),2)
        self.assertFalse(source.is_symlink());self.assertEqual((source/'saves/game.sav').read_text(),'save')
    def test_verified_switch_retains_original_and_is_idempotent(self):
        source,target=self.tree()
        with patch.object(storage_ops,'_emu_mount',return_value=(target.parent,'DECK-EMU')):
            self.assertEqual(storage_ops.finalize_emulation(True),0);self.assertEqual(source.resolve(),target)
            self.assertEqual(storage_ops.finalize_emulation(True),0)
            self.assertEqual(storage_ops.verify_migration()['status'],'VERIFIED')
        copies=list(self.home.glob('Emulation.pre-deckctl-*'));self.assertEqual(len(copies),1)
        self.assertEqual((copies[0]/'saves/game.sav').read_text(),'save')
    def test_missing_card_and_wrong_link_never_mutate(self):
        source,target=self.tree()
        with patch.object(storage_ops,'_emu_mount',return_value=(None,'DECK-EMU')):
            with self.assertRaises(ValueError):storage_ops.finalize_emulation(True)
        shutil.rmtree(source);source.symlink_to(self.home/'wrong')
        with patch.object(storage_ops,'_emu_mount',return_value=(target.parent,'DECK-EMU')):
            with self.assertRaises(ValueError):storage_ops.finalize_emulation(True)
        self.assertEqual(os.readlink(source),str(self.home/'wrong'))
    def test_source_changes_after_plan_detected(self):
        source,target=self.tree();expected=file_state.inventory(source)
        core.save_json(core.STATE/'emulation-migration.json',{'target':str(target),'inventory':expected})
        (source/'saves/game.sav').write_text('newer save')
        with patch.object(storage_ops,'_emu_mount',return_value=(target.parent,'DECK-EMU')):self.assertEqual(storage_ops.verify_migration()['status'],'CONFIG_REQUIRED')

class Shortcuts(Fixture):
    def vdf(self,user='1'):
        raw=b'\x01appname\0Fixture\0\x01exe\0"/missing/game"\0\x02appid\0'+struct.pack('<i',-123)+b'\x00tags\0\x010\0keep tag\0\x08\x08'
        data=b'\x00shortcuts\0\x000\0'+raw+b'\x001\0'+raw+b'\x08\x08'
        path=self.home/f'.local/share/Steam/userdata/{user}/config/shortcuts.vdf';path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);return path,data
    def test_audit_detects_missing_target_duplicate_without_writes(self):
        path,raw=self.vdf();data=shortcut_ops.audit(True)
        self.assertEqual(data['steam'][0]['target'],'MISSING');self.assertTrue(data['steam'][1]['exact_duplicate'])
        self.assertEqual(path.read_bytes(),raw);self.assertFalse(core.STATE.exists())
    def test_duplicate_preview_then_repair_retains_fields_and_backup(self):
        path,raw=self.vdf()
        with patch.object(shortcut_ops,'_steam_running',return_value=False):
            self.assertEqual(shortcut_ops.repair(duplicates=True),2);self.assertEqual(path.read_bytes(),raw)
            self.assertEqual(shortcut_ops.repair(yes=True,duplicates=True),0)
            self.assertEqual(shortcut_ops.repair(yes=True,duplicates=True),0)
        entries=shortcut_ops.library.shortcuts();self.assertEqual(len(entries),1);self.assertEqual(entries[0]['tags'],{'0':'keep tag'});self.assertEqual(entries[0]['appid'],-123)
        self.assertEqual(next((core.STATE/'shortcut-rollback').glob('*/*')).read_bytes(),raw)
    def test_running_steam_blocks_all_repairs(self):
        path,raw=self.vdf()
        with patch.object(shortcut_ops,'_steam_running',return_value=True):
            with self.assertRaises(ValueError):shortcut_ops.repair(yes=True,duplicates=True)
        self.assertEqual(path.read_bytes(),raw)
    def test_account_filter_keeps_other_account(self):
        first,_=self.vdf('1');second,raw=self.vdf('2')
        with patch.object(shortcut_ops,'_steam_running',return_value=False):shortcut_ops.repair(yes=True,duplicates=True,user='1')
        self.assertEqual(second.read_bytes(),raw);self.assertNotEqual(first.read_bytes(),raw)
    def test_managed_icon_repair_does_not_change_exec_or_steam_art(self):
        path=self.write(self.home/'Desktop/deck-media-netflix.desktop','[Desktop Entry]\nExec=/missing/browser --app=test\nIcon=missing\n')
        art=self.write(self.home/'.local/share/Steam/userdata/1/config/grid/test.png','art')
        with patch.object(shortcut_ops.desktop,'desktop_dir',return_value=self.home/'Desktop'):self.assertEqual(shortcut_ops.repair(yes=True),0)
        self.assertIn('Exec=/missing/browser --app=test',path.read_text());self.assertEqual(art.read_text(),'art')

class UpgradeAndBootstrap(Fixture):
    def test_upgrade_preview_preserves_config_and_lists_selection_additions(self):
        old=self.home/'old';self.write(old/'VERSION','0.2.24');self.write(old/'unchanged','same')
        candidate=self.home/'new';self.write(candidate/'VERSION','0.2.26');self.write(candidate/'unchanged','same');self.write(candidate/'new','new')
        self.write(candidate/'modules/decky/plugins.json',json.dumps({'selection_upgrades':[{'manifest_schema_version':5,'add_folders':['TabMaster']}],'recommended':[{'folder':'TabMaster','name':'TabMaster'}]}))
        config=core._decky_selection_path();self.write(config,json.dumps({'manifest_schema_version':4,'selected_folders':['Bluetooth']}));before=config.read_bytes()
        result=upgrade_plan.compare(candidate,old)
        self.assertEqual(result['decky_additions'],['TabMaster']);self.assertIn('VERSION',result['changed_files']);self.assertIn('new',result['added_files']);self.assertEqual(config.read_bytes(),before)
    def bootstrap(self):
        source=(ROOT/'bootstrap.sh').read_text().split("<<'PY'\n",1)[1].rsplit('\nPY',1)[0]
        ns={'__name__':'bootstrap_fixture'};exec(compile(source,'bootstrap.sh','exec'),ns);return ns
    def test_bootstrap_checksums_before_extract(self):
        ns=self.bootstrap();version='0.2.26';tarname=f'steamdeck-workstation-v{version}.tar.gz';sumname=f'steamdeck-workstation-v{version}-SHA256SUMS.txt'
        with patch.dict(ns,{'fetch':lambda *a:(('0'*64)+'  '+tarname+'\n').encode()}),patch.object(ns['urllib'].request,'urlopen',return_value=io.BytesIO(b'corrupt')):
            with self.assertRaises(ValueError):ns['download'](self.home,version,{tarname:'https://example.test/archive',sumname:'https://example.test/sums'})
        self.assertFalse((self.home/'steamdeck-workstation-0.2.26').exists())
    def test_bootstrap_verified_archive_extracts_permissions(self):
        ns=self.bootstrap();version='0.2.26';tarname=f'steamdeck-workstation-v{version}.tar.gz';sumname=f'steamdeck-workstation-v{version}-SHA256SUMS.txt'
        data=io.BytesIO()
        with tarfile.open(fileobj=data,mode='w:gz') as tf:
            for name,content,mode in [('VERSION',b'0.2.26',0o644),('install.sh',b'#!/bin/bash\n',0o755),('bin/deckctl',b'#!/bin/bash\n',0o755)]:
                info=tarfile.TarInfo('steamdeck-workstation-0.2.26/'+name);info.size=len(content);info.mode=mode;tf.addfile(info,io.BytesIO(content))
        raw=data.getvalue();sums=(hashlib.sha256(raw).hexdigest()+'  '+tarname+'\n').encode()
        with patch.dict(ns,{'fetch':lambda *a:sums}),patch.object(ns['urllib'].request,'urlopen',return_value=io.BytesIO(raw)):
            archive=ns['download'](self.home,version,{tarname:'https://example.test/archive',sumname:'https://example.test/sums'})
        root=ns['extract'](archive,self.home,version)
        self.assertEqual((root/'VERSION').read_text(),version)
        self.assertTrue(os.access(root/'bin/deckctl',os.X_OK))
    def test_bootstrap_rejects_wrong_asset_source(self):
        ns=self.bootstrap();payload={'tag_name':'v0.2.26','assets':[{'name':'steamdeck-workstation-v0.2.26.tar.gz','browser_download_url':'https://other.test/payload'}]}
        with patch.dict(ns,{'fetch':lambda *a:json.dumps(payload).encode()}):
            with self.assertRaises(ValueError):ns['resolve']()
    def test_bootstrap_rejects_traversal(self):
        ns=self.bootstrap();archive=self.home/'bad.tar.gz'
        with tarfile.open(archive,'w:gz') as tf:tf.addfile(tarfile.TarInfo('../escape'))
        with self.assertRaises(ValueError):ns['extract'](archive,self.home,'0.2.26')
    def test_preservation_of_previous_release(self):
        guard=json.loads((ROOT/'tests/fixtures/baseline-v0.2.25.json').read_text());changed=set()
        for name,entry in guard['files'].items():
            path=ROOT/name;self.assertTrue(path.is_file(),name);self.assertEqual(path.stat().st_mode & 0o777,entry['mode'],name)
            if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:changed.add(name)
        self.assertEqual(changed,set(guard['reliability_changes']) & set(guard['files']))
        for name in ['lib/deckctl/android.py','lib/deckctl/setup_cleanup.py','modules/decky/plugins.json','tools/install-control-plane']:
            if name == 'tools/install-control-plane':
                # Only the explicit RC suffix grammar changed; retain the historical
                # full-file guard for every other byte of the control plane.
                original = (ROOT/name).read_bytes().replace(br'\d+\.\d+\.\d+(?:-rc[1-9]\d*)?', br'\d+\.\d+\.\d+')
                self.assertEqual(hashlib.sha256(original).hexdigest(), guard['files'][name]['sha256'])
            else:
                self.assertNotIn(name,changed)

if __name__=='__main__':unittest.main(verbosity=2)
