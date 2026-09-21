#!/usr/bin/env python3
"""Review regressions: actual resulting state, isolated HOME, no vendor installs."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'lib'))
from deckctl import cli, core, controller, reliability, hostkit, terminal, storage_ops, lifecycle, desktop
from deckctl.helptext import walk, PAGES

class Review(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        for module,name,value in [(core,'STATE',self.home/'state'),(core,'CONFIG_HOME',self.home/'config'),(reliability,'CSS_DIR',self.home/'themes'),(reliability,'CSS_SNAPSHOTS',self.home/'config/css-profiles'),(reliability,'PROFILE_EXPORT_DIR',self.home/'exports')]:
            patcher=patch.object(module,name,value);patcher.start();self.addCleanup(patcher.stop)
        patcher=patch.dict(os.environ,{'HOME':str(self.home),'DECKCTL_CONFIG':str(self.home/'config'),'DECKCTL_STATE':str(self.home/'state'),'PYTHONDONTWRITEBYTECODE':'1'});patcher.start();self.addCleanup(patcher.stop)
    def run_cli(self,*args):
        return subprocess.run([str(ROOT/'bin/deckctl'),*args],capture_output=True,text=True,timeout=30)
    def archive(self,files):
        path=self.home/'profile.zip'
        with zipfile.ZipFile(path,'w') as z:
            z.writestr('manifest.json',json.dumps({'format':1}))
            for name,data in files.items():z.writestr('deckctl-config/'+name,data)
        return path
    def test_every_command_has_help_and_help_is_read_only(self):
        parser=cli.build_parser();paths=list(walk(parser))
        self.assertGreater(len(paths),100)
        for path,p in paths:
            with self.subTest(path=path):
                result=self.run_cli(*path,'--help')
                self.assertEqual(result.returncode,0,result.stderr)
                for section in ('NAME','DESCRIPTION','EXAMPLES','FILES','EXIT STATUS','SEE ALSO'):
                    self.assertIn(section,result.stdout)
                alias=self.run_cli('help',*path)
                self.assertEqual(alias.stdout,result.stdout)
        self.assertEqual(list(self.home.iterdir()),[])
    def test_help_errors_version_and_no_abbreviations(self):
        self.assertEqual(self.run_cli('--version').stdout.strip(),'0.2.33')
        self.assertEqual(self.run_cli('help','unknown').returncode,2)
        self.assertEqual(self.run_cli('terminal','apply','--config-o').returncode,2)
        self.assertEqual(self.run_cli('remote','register','desk').returncode,2)
    def test_generated_manual_has_no_drift(self):
        subprocess.run([sys.executable,str(ROOT/'tools/render-command-docs.py'),'--check'],check=True)
    def test_user_entrypoint_help_is_safe(self):
        names=['install.sh','bootstrap.sh','uninstall.sh','tools/install-control-plane','tools/build-release','tools/package-release.py','tools/verify-release.py','tools/validate-modules','tools/lint-docs','tools/redact-support-bundle','tools/sync-ai-instructions','tools/render-command-docs.py','tools/check-docs.py']
        for name in names:
            result=subprocess.run([str(ROOT/name),'--help'],capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,(name,result.stderr))
            self.assertTrue(result.stdout)
        self.assertEqual(list(self.home.iterdir()),[])
    def test_apply_reports_failure_and_continues(self):
        with patch.object(core,'enabled_modules',return_value=['first','second']),patch.object(core,'topo',side_effect=lambda x:x),patch.object(core,'run_action',side_effect=[subprocess.CompletedProcess([],1),subprocess.CompletedProcess([],0)]) as run,patch.object(core,'create_setup_shortcut'),patch.object(core,'module_status',return_value={'status':'READY'}):
            self.assertEqual(core.apply(),1);self.assertEqual(run.call_count,2)
    def test_verify_exit_contract(self):
        for status,expected in [('READY',0),('OPTIONAL',0),('FAILED',1),('NOT_INSTALLED',1),('CONFIG_REQUIRED',2),('DEGRADED',2)]:
            with patch.object(core,'verify',return_value={'test':{'status':status}}):self.assertEqual(cli.main(['verify']),expected)
    def test_failed_or_invalid_verifier_cannot_claim_ready(self):
        for proc in [subprocess.CompletedProcess([],1,'{"status":"READY"}',''),subprocess.CompletedProcess([],0,'{"status":"magic"}','')]:
            with patch.object(core,'run_action',return_value=proc):self.assertEqual(core.module_status('any')['status'],'FAILED')
        with patch.object(core,'run_action',side_effect=subprocess.TimeoutExpired('verify',60)):
            self.assertEqual(core.module_status('any')['status'],'FAILED')
    def test_status_and_controller_verify_do_not_create_files(self):
        for args in [('controller','status'),('setup','status')]:
            self.assertEqual(self.run_cli(*args).returncode,0)
        self.assertFalse(core.STATE.exists());self.assertFalse(core.CONFIG_HOME.exists())
        steam=self.home/'.local/share/Steam';steam.mkdir(parents=True)
        subprocess.run(['bash',str(ROOT/'modules/controller/verify.sh')],env={**os.environ,'DECKCTL_ROOT':str(ROOT)},check=True,capture_output=True)
        self.assertFalse((self.home/'.config').exists())
    def test_atomic_json_is_private_and_complete(self):
        path=core.CONFIG_HOME/'settings.json'
        core.save_json(path,{'a':1});core.save_json(path,{'b':2})
        self.assertEqual(json.loads(path.read_text()),{'b':2});self.assertEqual(path.stat().st_mode&0o777,0o600)
        self.assertEqual([p.name for p in path.parent.iterdir()],['settings.json'])
    def test_profile_export_allowlist_and_roundtrip(self):
        core.CONFIG_HOME.mkdir()
        (core.CONFIG_HOME/'settings.json').write_text(json.dumps({'password':'TOPSECRET','profile':'oled'}))
        unknown=core.CONFIG_HOME/'private';unknown.mkdir();(unknown/'key.pem').write_text('TOPSECRET')
        shell=core.CONFIG_HOME/'shell';shell.mkdir();(shell/'evil.sh').write_text('TOPSECRET')
        layouts=core.CONFIG_HOME/'controller-layouts';layouts.mkdir();(layouts/'mine.vdf').write_text('"controller_mappings" {}')
        (core.CONFIG_HOME/'games.json').write_text('invalid json TOPSECRET')
        (core.CONFIG_HOME/'hosts.json').symlink_to(unknown/'key.pem')
        arc=reliability.profile_export()
        with zipfile.ZipFile(arc) as z:
            names=z.namelist();self.assertIn('deckctl-config/controller-layouts/mine.vdf',names)
            self.assertFalse(any('TOPSECRET' in z.read(n).decode() for n in names))
            self.assertNotIn('deckctl-config/games.json',names)
        (core.CONFIG_HOME/'settings.json').write_text('{"profile":"lcd"}')
        reliability.profile_import(str(arc))
        self.assertEqual(json.loads((core.CONFIG_HOME/'settings.json').read_text())['profile'],'oled')
        backups=list((core.STATE/'profile-import-rollback').glob('*/settings.json'))
        self.assertEqual(json.loads(backups[0].read_text())['profile'],'lcd')
    def test_profile_import_preflight_prevents_partial_write(self):
        core.save_json(core.CONFIG_HOME/'settings.json',{'profile':'lcd'})
        arc=self.archive({'settings.json':'{"profile":"oled"}','shell/evil.sh':'touch /tmp/evil'})
        with self.assertRaises(ValueError):reliability.profile_import(str(arc))
        self.assertEqual(core.load_json(core.CONFIG_HOME/'settings.json')['profile'],'lcd')
    def test_profile_import_rejects_destination_symlinks(self):
        core.CONFIG_HOME.mkdir();outside=self.home/'outside';outside.write_text('{}')
        (core.CONFIG_HOME/'settings.json').symlink_to(outside)
        arc=self.archive({'settings.json':'{"profile":"oled"}'})
        with self.assertRaises(ValueError):reliability.profile_import(str(arc))
        self.assertEqual(outside.read_text(),'{}')
    def test_profile_names_cannot_escape(self):
        for name in ('../outside','/outside','..','a\\b'):
            with self.assertRaises(ValueError):reliability._resolve_profile(self.home,name)
    def test_zip_traversal_duplicates_and_links_rejected(self):
        for name in ('../x','/absolute','a\\b'):
            zpath=self.home/'bad.zip'
            with zipfile.ZipFile(zpath,'w') as z:z.writestr(name,'x')
            with zipfile.ZipFile(zpath) as z,self.assertRaises(RuntimeError):reliability._safe_zip_extract(z,self.home/'out')
        with zipfile.ZipFile(zpath,'w') as z:
            info=zipfile.ZipInfo('link');info.external_attr=0o120777<<16;z.writestr(info,'target')
        with zipfile.ZipFile(zpath) as z,self.assertRaises(RuntimeError):reliability._safe_zip_extract(z,self.home/'out')
    def test_release_special_files_rejected(self):
        path=self.home/'bad.tar.gz'
        with tarfile.open(path,'w:gz') as tar:
            info=tarfile.TarInfo('repo/fifo');info.type=tarfile.FIFOTYPE;tar.addfile(info)
        with self.assertRaises(RuntimeError):reliability._extract_release(path,self.home/'out')
    def test_rollback_ignores_empty_and_outside_history(self):
        releases=self.home/'releases';releases.mkdir()
        history=self.home/'history.json';history.write_text(json.dumps({'events':[{'from':None},{'from':str(ROOT)}]}))
        with patch.object(reliability,'RELEASES_DIR',releases),patch.object(reliability,'UPDATE_HISTORY',history),patch.object(reliability,'CURRENT_LINK',self.home/'current'),patch.object(reliability.subprocess,'run') as run:
            self.assertEqual(reliability.update_rollback(),2);run.assert_not_called()
    def test_hostkit_cannot_delete_unregistered_paths(self):
        for name in ('../outside','/tmp/escape','unregistered'):
            with self.assertRaises(SystemExit):hostkit.build(name)
        self.assertFalse(core.STATE.exists())
    def test_remote_relay_quotes_one_command(self):
        with patch.object(core,'get_host',return_value={'mac':'AA:BB:CC:DD:EE:FF','relay_ssh':'deck@host'}),patch.object(core.subprocess,'run') as run:
            core.remote_wake('test');args=run.call_args.args[0]
            self.assertEqual(args[:3],['ssh','--','deck@host'])
            remote=shlex.split(args[3]);self.assertEqual(remote[:2],['python3','-c']);compile(remote[2],'<remote>','exec')
        with self.assertRaises(SystemExit):core.remote_register('bad','-oProxyCommand=bad')
        with self.assertRaises(SystemExit):core.remote_register('bad','host',sunshine_port=70000)
    def test_terminal_failed_update_keeps_old_binary(self):
        bindir=self.home/'bin';bindir.mkdir();dest=bindir/'testtool';dest.write_bytes(b'known good')
        buf=io.BytesIO()
        with tarfile.open(fileobj=buf,mode='w:gz') as tar:
            data=b'#!/bin/sh\nexit 1\n';info=tarfile.TarInfo('testtool');info.size=len(data);info.mode=0o755;tar.addfile(info,io.BytesIO(data))
        with patch.object(terminal,'BIN_DIR',bindir),patch.object(terminal,'_github_asset',return_value=({'tag_name':'v1'},{'browser_download_url':'test','name':'test.tgz'})),patch.object(terminal,'_request',return_value=buf.getvalue()):
            with self.assertRaises(RuntimeError):terminal._install_binary_asset('test','.*','testtool',verify_args=('--version',))
        self.assertEqual(dest.read_bytes(),b'known good');self.assertEqual(list(bindir.iterdir()),[dest])
    def test_existing_migration_link_is_preserved(self):
        target=self.home/'card/Emulation';(target/'roms').mkdir(parents=True);(target/'bios').mkdir()
        source=self.home/'Emulation';source.symlink_to(target)
        with patch.object(storage_ops,'_emu_mount',return_value=(self.home/'card','DECK-EMU')):
            self.assertEqual(storage_ops.finalize_emulation(True),0)
        self.assertTrue(source.is_symlink())
    def test_restore_rejects_unsupported_categories_and_versions(self):
        for manifest in ({'format':1,'categories':{}},{'format':2,'categories':{'evil':{'source':str(self.home/'.bashrc')}}}):
            path=self.home/'backup.tgz'
            with tarfile.open(path,'w:gz') as tar:
                raw=json.dumps(manifest).encode();info=tarfile.TarInfo('deckctl-backup-manifest.json');info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
            with self.assertRaises(ValueError),patch.object(lifecycle,'_select') as select:lifecycle.restore(str(path))
            select.assert_not_called()
    def test_control_plane_install_repeatability_conflict_and_man_page(self):
        tool=ROOT/'tools/install-control-plane'
        for _ in range(2):
            result=subprocess.run([str(tool),str(ROOT)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
        current=self.home/'.local/share/steamdeck-workstation/current'
        self.assertTrue(current.is_symlink());self.assertTrue((self.home/'.local/share/man/man1/deckctl.1').is_file())
        self.assertEqual((self.home/'.bashrc').read_text().count('# >>> steamdeck-workstation deckctl >>>'),1)
        (current/'README.md').write_text('local modification')
        result=subprocess.run([str(tool),str(ROOT)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertEqual((current/'README.md').read_text(),'local modification')
    def test_desktop_exec_literal_encoding(self):
        # Interpret the two standardized escaping layers, then compare literal argv.
        values=['konsole','a b','quote"here',r'a\b','$HOME','100%','`cmd`']
        encoded=desktop.exec_line(values)
        first=encoded.replace('\\\\','\\')
        decoded=shlex.split(first)
        decoded=[x.replace('\\$','$').replace('\\`','`').replace('%%','%') for x in decoded]
        self.assertEqual(decoded,values)
    def test_restore_result_and_previous_content_retained(self):
        source=self.home/'source';source.mkdir();(source/'save.dat').write_text('restored save')
        dest=self.home/'Emulation/saves';dest.mkdir(parents=True);(dest/'save.dat').write_text('current save')
        path=self.home/'backup.tgz'
        manifest={'format':2,'categories':{'emulation-saves':{'source':str(dest),'arc':'payload/emulation-saves'}}}
        with tarfile.open(path,'w:gz') as tar:
            tar.add(source,arcname='payload/emulation-saves')
            raw=json.dumps(manifest).encode();info=tarfile.TarInfo('deckctl-backup-manifest.json');info.size=len(raw);tar.addfile(info,io.BytesIO(raw))
        with patch.object(lifecycle,'_select',return_value={'emulation-saves'}),patch.object(lifecycle,'_emu_root',return_value=self.home/'Emulation'):
            self.assertEqual(lifecycle.restore(str(path)),0)
        self.assertEqual((dest/'save.dat').read_text(),'restored save')
        rollback=list((core.STATE/'restore-rollback').glob('*/emulation-saves/save.dat'))
        self.assertEqual(rollback[0].read_text(),'current save')
    def test_profile_import_write_failure_rolls_back(self):
        core.save_json(core.CONFIG_HOME/'settings.json',{'profile':'lcd'})
        core.save_json(core.CONFIG_HOME/'games.json',{'old':True})
        archive=self.archive({'games.json':'{"new":true}','settings.json':'{"profile":"oled"}'})
        real_replace=Path.replace
        def fail_second(path,dest):
            if Path(dest).name=='settings.json' and path.name.startswith('.profile-'): raise OSError('simulated disk error')
            return real_replace(path,dest)
        with patch.object(Path,'replace',fail_second),self.assertRaises(OSError):reliability.profile_import(str(archive))
        self.assertEqual(core.load_json(core.CONFIG_HOME/'settings.json'),{'profile':'lcd'})
        self.assertEqual(core.load_json(core.CONFIG_HOME/'games.json'),{'old':True})
    def test_tailscale_failed_refresh_preserves_existing_tree(self):
        old=self.home/'deck-tailscale';old.mkdir();(old/'personal.txt').write_text('keep')
        fake=self.home/'bin';fake.mkdir();git=fake/'git';git.write_text('#!/bin/sh\nexit 7\n');git.chmod(0o755)
        result=subprocess.run(['bash',str(ROOT/'modules/remote/install-tailscale-steamos.sh')],env={**os.environ,'PATH':str(fake)+':'+os.environ['PATH']},capture_output=True,text=True)
        self.assertEqual(result.returncode,7);self.assertEqual((old/'personal.txt').read_text(),'keep')
        self.assertEqual(list(self.home.glob('.deck-tailscale-stage.*')),[])
    def test_profile_zip_duplicate_paths_and_budget(self):
        import warnings
        path=self.home/'duplicate.zip'
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with zipfile.ZipFile(path,'w') as z:
                z.writestr('same','one');z.writestr('same','two')
        with zipfile.ZipFile(path) as z,self.assertRaises(RuntimeError):reliability._safe_zip_extract(z,self.home/'out')
        entry=zipfile.ZipInfo('huge');entry.file_size=257*1024*1024
        with patch.object(zipfile.ZipFile,'infolist',return_value=[entry]):
            with zipfile.ZipFile(path) as z,self.assertRaises(RuntimeError):reliability._safe_zip_extract(z,self.home/'out')
    def test_workspace_verify_machine_contract(self):
        result=subprocess.run(['bash',str(ROOT/'modules/workspace/verify.sh')],env={**os.environ,'DECKCTL_ROOT':str(ROOT)},capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'CONFIG_REQUIRED')
    def test_terminal_reset_does_not_trust_receipt_path(self):
        # Verify the actual reset operation cannot remove an outside file even
        # when its hash matches a forged managed-tool receipt.
        private=self.home/'private.txt';private.write_text('keep')
        receipt=self.home/'receipt.json';receipt.write_text(json.dumps({'fzf':{'path':str(private),'binary_sha256':hashlib.sha256(private.read_bytes()).hexdigest()}}))
        names=['BASHRC','TMUXRC','SHELL_CONFIG','TMUX_CONFIG','STARSHIP_CONFIG','POSH_CONFIG','PROMPT_ENGINE_FILE','KONSOLERC','STATE_FILE']
        with contextlib.ExitStack() as stack:
            for name in names:stack.enter_context(patch.object(terminal,name,self.home/name.lower()))
            stack.enter_context(patch.object(terminal,'KONSOLE_DIR',self.home/'konsole'))
            stack.enter_context(patch.object(terminal,'FONT_DIR',self.home/'fonts'))
            stack.enter_context(patch.object(terminal,'RECEIPTS_FILE',receipt))
            stack.enter_context(patch.object(terminal.shutil,'which',return_value=None))
            self.assertEqual(terminal.reset(),0)
        self.assertEqual(private.read_text(),'keep')
    def test_baseline_preserved_outside_explicit_review_changes(self):
        guard=json.loads((ROOT/'tests/fixtures/baseline-v0.2.19.json').read_text())
        changed=set()
        for name,sha in guard['files'].items():
            self.assertTrue((ROOT/name).is_file(),name)
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=sha:changed.add(name)
        patch_changes=set(json.loads((ROOT/'tests/fixtures/baseline-v0.2.21.json').read_text())['provisioning_changes'])
        patch_changes.update(json.loads((ROOT/'tests/fixtures/baseline-v0.2.22.json').read_text())['maintenance_changes'])
        patch_changes.update(json.loads((ROOT/'tests/fixtures/baseline-v0.2.23.json').read_text())['maintenance_changes'])
        patch_changes.update(json.loads((ROOT/'tests/fixtures/baseline-v0.2.24.json').read_text())['plugin_changes'])
        patch_changes.update(json.loads((ROOT/'tests/fixtures/baseline-v0.2.25.json').read_text())['reliability_changes'])
        self.assertEqual(changed-patch_changes,set(guard['reviewed_changes'])-patch_changes)

if __name__=='__main__':unittest.main(verbosity=2)
