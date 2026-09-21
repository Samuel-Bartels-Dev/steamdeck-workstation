#!/usr/bin/env python3
"""Install boundaries for individually selected tools; never runs vendor installers."""
import contextlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'lib'))
from deckctl import component_options as options, core, setup_builder, terminal, provisioning, workspace


class Components(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.home=Path(self.temp.name)
        p=patch.object(core,'CONFIG_HOME',self.home/'config'); p.start(); self.addCleanup(p.stop)

    def save(self, **groups):
        choices={key: [] for key in options.CATALOG}; choices.update(groups)
        setup_builder.save_plan(['terminal'], [], components=choices)

    def test_ghostty_only_never_downloads_other_tools_or_changes_shell(self):
        self.save(terminal=['ghostty'])
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(terminal,'BIN_DIR',self.home/'bin'))
            stack.enter_context(patch.object(terminal,'RECEIPTS_FILE',self.home/'receipts.json'))
            stack.enter_context(patch.object(terminal.os,'geteuid',return_value=1000))
            stack.enter_context(patch.object(terminal,'_unmanaged_local_binary',return_value=False))
            stack.enter_context(patch.object(terminal,'_receipt_binary_ok',return_value=False))
            download=stack.enter_context(patch.object(terminal,'_install_appimage',return_value={}))
            config=stack.enter_context(patch.object(terminal,'_copy_managed_config'))
            stack.enter_context(patch.object(terminal,'_ghostty_desktop'))
            for name in ('_install_binary_asset','_install_fonts','_install_oh_my_posh','_install_starship','_install_zoxide',
                         '_install_shell_block','_install_tmux_block','_set_konsole_default'):
                stack.enter_context(patch.object(terminal,name,side_effect=AssertionError(name+' must not run')))
            self.assertEqual(terminal.apply(),0)
            self.assertEqual(download.call_args.args[-1],'ghostty')
            download.assert_called_once()
            config.assert_called_once_with({'ghostty'})

    def test_invalid_components_and_failed_final_write_leave_plan_unchanged(self):
        self.save(terminal=['tmux'])
        before={p.name:p.read_bytes() for p in core.CONFIG_HOME.iterdir()}
        with self.assertRaises(ValueError): self.save(terminal=['unknown'])
        save=core.save_json
        def fail(path,data):
            if path.name=='components.json': raise OSError('disk full')
            return save(path,data)
        with patch.object(core,'save_json',side_effect=fail), self.assertRaises(OSError):
            self.save(terminal=['ghostty'])
        self.assertEqual(before,{p.name:p.read_bytes() for p in core.CONFIG_HOME.iterdir()})

    def test_guided_setup_skips_unselected_tools_inside_enabled_categories(self):
        self.save(remote=['moonlight'],dev=[],workspace=[],media=[])
        enabled={'remote','dev','workspace','media'}
        for sid, module in [('tailscale','remote'),('chiaki','remote'),('codex','dev'),('keeper','media'),('workspace','workspace'),('media','media')]:
            self.assertFalse(provisioning.selected({'id':sid,'module':module},enabled))
        self.assertTrue(provisioning.selected({'id':'moonlight','module':'remote'},enabled))

    def test_empty_terminal_is_ready_and_status_does_not_require_unselected_commands(self):
        self.save()
        with patch.object(terminal,'_font_match',return_value=''), patch.object(terminal.shutil,'which',return_value=None):
            self.assertEqual(terminal.status_data()['status'],'READY')
            self.assertEqual(terminal.status(),0)

    def test_ai_dependencies_only_add_opencode_and_selected_model_engine(self):
        self.save(**{'ai-workspace':['model']})
        with patch.object(core,'enabled_modules',return_value=['ai-workspace']):
            self.assertEqual(options.effective('terminal'),{'opencode'})
            self.assertEqual(options.effective('ai-workspace'),{'model','ollama'})

    def test_empty_workspace_does_not_install_chrome(self):
        self.save(workspace=[])
        with patch.object(workspace,'_chrome',side_effect=AssertionError('No browser needed')):
            self.assertEqual(workspace.setup(),0)

    def test_keeper_alone_installs_its_browser_dependency(self):
        self.save(media=['keeper'])
        with patch.object(core,'_flatpak_installed',return_value=False), patch.object(core.subprocess,'run') as run, patch.object(core.subprocess,'Popen'):
            run.return_value.returncode=0
            self.assertEqual(core.media_keeper_setup(),0)
            run.assert_called_once_with(['flatpak','install','--user','-y','flathub','com.google.Chrome'])

    def test_media_helper_empty_selection_never_installs_browser(self):
        self.save(media=[])
        helper=self.home/'.local/share/deckctl/media'; helper.mkdir(parents=True)
        (helper/'services.json').write_bytes((core.ROOT/'modules/media/services.json').read_bytes())
        bindir=self.home/'bin'; bindir.mkdir()
        flatpak=bindir/'flatpak'; flatpak.write_text('#!/bin/sh\ntouch "$HOME/unwanted-browser"\nexit 1\n'); flatpak.chmod(0o755)
        env=dict(os.environ,HOME=str(self.home),DECKCTL_CONFIG=str(core.CONFIG_HOME),PATH=str(bindir)+':'+os.environ['PATH'])
        result=subprocess.run(['bash',str(core.ROOT/'modules/media/setup-media.sh'),'--all'],env=env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse((self.home/'unwanted-browser').exists())

    def test_remote_shell_only_installs_selected_client(self):
        self.save(remote=['moonlight'])
        bindir=self.home/'bin'; bindir.mkdir()
        script=bindir/'flatpak'
        script.write_text('#!/bin/sh\nif [ "$1" = info ]; then exit 1; fi\nprintf "%s\\n" "$*" >> "$HOME/calls"\n')
        script.chmod(0o755)
        env=dict(os.environ,HOME=str(self.home),DECKCTL_ROOT=str(core.ROOT),DECKCTL_CONFIG=str(core.CONFIG_HOME),PATH=str(bindir)+':'+os.environ['PATH'])
        result=subprocess.run(['bash',str(core.ROOT/'modules/remote/install.sh')],env=env,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual((self.home/'calls').read_text().splitlines(),['install --user -y flathub com.moonlight_stream.Moonlight'])
        self.assertFalse((self.home/'Desktop').exists())


if __name__=='__main__': unittest.main(verbosity=2)
