#!/usr/bin/env python3
"""Fake Steam handoffs and isolated VDF fixtures; no live Steam mutations."""
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'lib'))
from deckctl import app_shortcuts as shortcuts, core, desktop
REAL_POPEN = subprocess.Popen


def vdf(records):
    def obj(values):
        result = b''
        for key, value in values.items():
            if isinstance(value, dict): result += b'\x00'+key.encode()+b'\x00'+obj(value)
            elif isinstance(value, int): result += b'\x02'+key.encode()+b'\x00'+struct.pack('<i', value)
            else: result += b'\x01'+key.encode()+b'\x00'+value.encode()+b'\x00'
        return result+b'\x08'
    return obj({'shortcuts':{str(i):entry for i, entry in enumerate(records)}})


class AppShortcuts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(Path, 'home', return_value=self.home))
        self.stack.enter_context(patch.object(core, 'STATE', self.home/'state'))
        self.stack.enter_context(patch.object(shortcuts, 'MARKER', self.home/'marker'))
        self.which = self.stack.enter_context(patch.object(shortcuts.shutil, 'which', side_effect=lambda name: {'steamos-add-to-steam':'/fake/add', 'steam':'/fake/steam', 'flatpak':'/usr/bin/flatpak'}.get(name)))
        self.process = Mock(); self.process.wait.return_value = 0
        self.start = self.stack.enter_context(patch.object(shortcuts.subprocess, 'Popen', return_value=self.process))
        self.generation = self.stack.enter_context(patch.object(shortcuts, '_steam_generation', return_value=['123:456']))
        self.user = self.home/'.local/share/Steam/userdata/42/config'
        self.user.mkdir(parents=True)
        self.desktop = self.home/'.local/share/applications/discord.desktop'
        self.desktop.parent.mkdir(parents=True)
        self.write_desktop('/usr/bin/flatpak', 'run', 'com.discordapp.Discord')

    def write_desktop(self, *command, name='Discord'):
        self.desktop.write_text('[Desktop Entry]\nType=Application\nName='+name+'\nExec='+desktop.exec_line(command)+'\nIcon=old\n')

    def write_vdf(self, entries, user=None):
        target = (user or self.user)/'shortcuts.vdf'
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(vdf(entries))
        return target

    def ensure(self): return shortcuts.ensure('app:discord', 'Discord', self.desktop)
    def status(self): return shortcuts.status('app:discord', 'Discord', self.desktop)

    def test_submit_once_then_ready_only_after_saved_vdf(self):
        self.assertEqual(self.status(), 'MISSING'); self.start.assert_not_called()
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH')
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH')
        self.assertEqual(self.status(), 'PENDING_STEAM_REFRESH')
        self.start.assert_called_once()
        self.assertEqual(self.start.call_args.args[0], ['/fake/add', str(self.desktop)])
        self.assertTrue(self.start.call_args.kwargs['start_new_session'])
        self.write_vdf([{'appname':'Discord', 'exe':'"/usr/bin/flatpak"', 'LaunchOptions':'run com.discordapp.Discord'}])
        self.assertEqual(self.status(), 'READY'); self.assertEqual(self.ensure(), 'READY')
        self.start.assert_called_once()

    def test_exact_app_identity_preserves_custom_name_arguments_and_other_entries(self):
        target = self.write_vdf([{'appname':'My chat tile', 'exe':'"/usr/bin/flatpak"',
                                 'LaunchOptions':'run --branch=stable --arch=x86_64 --command=Discord com.discordapp.Discord --custom'},
                                {'appname':'Discord notes', 'exe':'/usr/bin/flatpak', 'LaunchOptions':'run com.other.App'}])
        before = target.read_bytes()
        self.assertEqual(self.ensure(), 'READY'); self.assertEqual(self.status(), 'READY')
        self.start.assert_not_called(); self.assertEqual(target.read_bytes(), before)

    def test_similar_names_and_unrelated_flatpak_never_count_ready(self):
        self.write_vdf([{'appname':'Discord', 'exe':'/usr/bin/flatpak', 'LaunchOptions':'run com.other.App'},
                        {'appname':'Discord helper', 'exe':'/usr/bin/other', 'LaunchOptions':''}])
        self.assertEqual(self.status(), 'MISSING')
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH')

    def test_receipt_changes_with_target_but_not_icons_or_deployment_symlink(self):
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH')
        self.desktop.write_text(self.desktop.read_text().replace('Icon=old', 'Icon=new'))
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH'); self.start.assert_called_once()
        self.write_desktop('/usr/bin/flatpak', 'run', 'com.other.App')
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH'); self.assertEqual(self.start.call_count, 2)
        deployment = self.desktop.parent/'deployment1.desktop'
        self.desktop.rename(deployment); self.desktop.symlink_to(deployment)
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH'); self.assertEqual(self.start.call_count, 2)
        replacement = self.desktop.parent/'deployment2.desktop'
        replacement.write_bytes(deployment.read_bytes()); self.desktop.unlink(); self.desktop.symlink_to(replacement)
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH'); self.assertEqual(self.start.call_count, 2)

    def test_helper_failure_and_cancellation_allow_retry_without_uri_fallback(self):
        for rc in (1, 130, -2):
            self.process.wait.return_value = rc
            with self.assertRaisesRegex(ValueError, 'failed or was cancelled'): self.ensure()
            self.assertEqual(self.status(), 'MISSING')
        self.process.wait.return_value = 0
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH')
        self.assertEqual(self.start.call_count, 4)
        self.assertTrue(all(call.args[0][0] == '/fake/add' for call in self.start.call_args_list))

    def test_failed_process_start_is_retryable(self):
        self.start.side_effect = OSError('launch failure')
        with self.assertRaisesRegex(ValueError, 'could not start'): self.ensure()
        self.assertEqual(self.status(), 'MISSING')
        self.start.side_effect = None
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH')

    def test_real_fake_helper_failure_retry_and_concurrent_submission(self):
        helper = self.home/'fake-helper'
        fail = self.home/'fail'; fail.touch()
        calls = self.home/'helper-calls'
        helper.write_text('#!'+sys.executable+'\nimport sys\nfrom pathlib import Path\n'
                          'with Path('+repr(str(calls))+').open("a") as out: out.write(sys.argv[1]+"\\n")\n'
                          'sys.exit(1 if Path('+repr(str(fail))+').exists() else 0)\n')
        helper.chmod(0o700)
        self.which.side_effect = lambda name: str(helper) if name == 'steamos-add-to-steam' else None
        self.start.side_effect = REAL_POPEN
        with self.assertRaisesRegex(ValueError, 'failed or was cancelled'): self.ensure()
        self.assertEqual(self.status(), 'MISSING')
        fail.unlink()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(lambda _: self.ensure(), range(2))), ['PENDING_STEAM_REFRESH']*2)
        self.assertEqual(calls.read_text().splitlines(), [str(self.desktop)]*2)

    def test_running_steam_handoff_and_interrupted_wait_never_kill_steam_or_duplicate(self):
        self.process.wait.side_effect = subprocess.TimeoutExpired(['/fake/add'], 5)
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH')
        self.process.kill.assert_not_called(); self.process.terminate.assert_not_called()
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH'); self.start.assert_called_once()
        self.write_desktop('/usr/bin/flatpak', 'run', 'com.other.App')
        self.process.wait.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt): self.ensure()
        self.assertEqual(self.status(), 'PENDING_STEAM_REFRESH')
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH')

    def test_manual_steam_restart_allows_retry_for_absent_shortcut(self):
        self.process.wait.side_effect = subprocess.TimeoutExpired(['/fake/add'], 5)
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH')
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH'); self.start.assert_called_once()
        self.generation.return_value = ['321:654']
        self.assertEqual(self.status(), 'MISSING')
        self.process.wait.side_effect = None
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH'); self.assertEqual(self.start.call_count, 2)

    def test_steam_not_running_never_launches_helper_or_steam(self):
        self.generation.return_value = []
        self.assertEqual(self.status(), 'MISSING')
        with self.assertRaisesRegex(ValueError, 'open Steam'): self.ensure()
        self.start.assert_not_called(); self.assertFalse(shortcuts._receipt_path().exists())

    def test_malformed_receipt_does_not_claim_pending(self):
        self.ensure()
        receipts = json.loads(shortcuts._receipt_path().read_text())
        receipts[next(iter(receipts))] = True
        shortcuts._receipt_path().write_text(json.dumps(receipts))
        with self.assertRaisesRegex(ValueError, 'submission is invalid'): self.status()
        with self.assertRaisesRegex(ValueError, 'submission is invalid'): self.ensure()
        self.start.assert_called_once()

    def test_steam_uri_fallback_encodes_absolute_path_and_marker(self):
        self.which.side_effect = lambda name: '/fake/steam' if name == 'steam' else None
        renamed = self.desktop.with_name('chat app.desktop'); self.desktop.rename(renamed); self.desktop = renamed
        self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH')
        self.assertTrue(shortcuts.MARKER.exists())
        args = self.start.call_args.args[0]
        self.assertEqual(args[0], '/fake/steam'); self.assertIn('%20', args[1]); self.assertIn('steam://addnonsteamgame/%2F', args[1])

    def test_verify_is_read_only_and_missing_install_never_submits(self):
        self.assertEqual(self.status(), 'MISSING'); self.assertFalse(core.STATE.exists())
        self.ensure()
        before = {p:p.read_bytes() for p in core.STATE.iterdir()}
        self.assertEqual(self.status(), 'PENDING_STEAM_REFRESH')
        self.assertEqual(before, {p:p.read_bytes() for p in core.STATE.iterdir()})
        self.start.reset_mock(); self.desktop.unlink()
        self.assertEqual(self.status(), 'MISSING')
        with self.assertRaisesRegex(ValueError, 'install the app'): self.ensure()
        self.start.assert_not_called()

    def test_most_recent_account_scoping_and_receipts(self):
        other = self.home/'.local/share/Steam/userdata/99/config'
        self.write_vdf([{'appname':'Discord', 'exe':'/usr/bin/flatpak', 'LaunchOptions':'run com.discordapp.Discord'}], other)
        login = self.home/'.local/share/Steam/config/loginusers.vdf'; login.parent.mkdir()
        login.write_text('"users"{"'+str(shortcuts.STEAM_BASE+42)+'"{"MostRecent" "1"}}')
        self.assertEqual(self.status(), 'MISSING'); self.assertEqual(self.ensure(), 'PENDING_STEAM_REFRESH')
        login.write_text('"users"{"'+str(shortcuts.STEAM_BASE+99)+'"{"MostRecent" "1"}}')
        self.assertEqual(self.status(), 'READY'); self.assertEqual(self.ensure(), 'READY')
        self.start.assert_called_once()

    def test_no_profile_is_missing_and_ambiguous_profile_fails_honestly(self):
        self.user.rmdir(); self.user.parent.rmdir()
        self.assertEqual(self.status(), 'MISSING')
        with self.assertRaisesRegex(ValueError, 'sign into Steam'): self.ensure()
        self.start.assert_not_called()
        self.user.mkdir(parents=True)
        (self.home/'.local/share/Steam/userdata/99/config').mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, 'ambiguous'): self.ensure()
        self.start.assert_not_called()

    def test_malformed_vdf_is_not_misreported_as_missing_or_submitted(self):
        target = self.write_vdf([{'appname':'Discord', 'exe':'/usr/bin/flatpak', 'LaunchOptions':'run com.discordapp.Discord'}])
        for data in (target.read_bytes()[:-2], b'not VDF', b'\x00shortcuts\x00'):
            target.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'could not be read'): self.status()
            with self.assertRaisesRegex(ValueError, 'could not be read'): self.ensure()
        self.start.assert_not_called(); self.assertFalse(shortcuts._receipt_path().exists())

    def test_non_string_target_fields_fail_with_clear_error(self):
        self.write_vdf([{'appname':'Discord', 'exe':123, 'LaunchOptions':''}])
        with self.assertRaisesRegex(ValueError, 'launch arguments'): self.status()
        with self.assertRaisesRegex(ValueError, 'launch arguments'): self.ensure()
        self.start.assert_not_called()

    def test_malformed_desktop_launcher_has_actionable_value_error(self):
        self.desktop.write_text('invalid desktop content\n')
        with self.assertRaisesRegex(ValueError, 'Discord: invalid desktop'): self.status()
        with self.assertRaisesRegex(ValueError, 'Discord: invalid desktop'): self.ensure()
        self.start.assert_not_called()

    def test_workspace_runner_with_spaces_matches_exact_path_and_preserves_arguments(self):
        runner = self.home/'.local/share/deckctl/workspace/bin/chat gpt'
        self.write_desktop(str(runner), name='ChatGPT')
        self.write_vdf([{'appname':'Personal assistant', 'exe':'"'+str(runner)+'"', 'LaunchOptions':'--custom'}])
        self.assertEqual(shortcuts.status('workspace:chatgpt', 'ChatGPT', self.desktop), 'READY')
        self.assertEqual(shortcuts.ensure('workspace:chatgpt', 'ChatGPT', self.desktop), 'READY')
        self.start.assert_not_called()


if __name__ == '__main__': unittest.main()
