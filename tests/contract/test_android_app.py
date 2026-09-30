#!/usr/bin/env python3
"""Android adapter and queue regressions; no real provider or host changes."""
from contextlib import nullcontext
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'lib'))
from deckctl import android, setup_install, setup_finish, privilege, user_session
import test_v0222 as android_fixtures


class AndroidApp(unittest.TestCase):
    launcher = android_fixtures.AndroidProvisioning.launcher

    def setUp(self):
        android_fixtures.AndroidProvisioning.setUp(self)
        self.stack.enter_context(patch.dict(os.environ, {'DECKCTL_UI_RUN':'1', 'DECKCTL_APP_SUDO':'test-owner'}))
        self.stack.enter_context(patch.object(user_session, 'nested_desktop', return_value=False))

    def test_nested_rejects_provider_and_launcher_before_authorization(self):
        with patch.object(user_session,'nested_desktop',return_value=True), patch.object(android,'_ensure_checkout') as checkout, patch.object(android.subprocess,'run') as run:
            self.assertEqual(android._run(),2)
            self.assertEqual(android._first_run(),2)
            row = {'key':'module:android','kind':'module','owner':'android'}
            with patch.object(setup_install,'verify',return_value=False), patch.object(privilege,'command') as authorize:
                with self.assertRaisesRegex(setup_install.NeedsSetup,'Nested Desktop'): setup_install.execute(row)
                authorize.assert_not_called()
            checkout.assert_not_called(); run.assert_not_called()

    def test_ui_launcher_zero_exit_requires_state_and_nonzero_stays_failure(self):
        with patch.object(android,'_app_launcher',side_effect=lambda: nullcontext(android.LAUNCHER)), patch.object(android,'_app_authorization_result',return_value=True):
            self.launcher('echo launcher-output\nexit 0')
            self.assertEqual(android.retry(),2)
            self.launcher('mkdir -p "$HOME/.local/share/waydroid"\nexit 7')
            self.assertEqual(android.retry(),7)

    def test_provider_cannot_report_success_after_suppressing_auth_failure(self):
        with patch.object(android,'_app_launcher',side_effect=lambda: nullcontext(android.LAUNCHER)), patch.object(android,'_app_authorization_result',return_value=False):
            self.assertEqual(android.retry(),2)
            self.assertTrue(android.STATE.exists())

    def test_redirected_provider_log_is_drained_into_shared_output(self):
        output = io.StringIO()
        with redirect_stdout(output), android._provider_output(self.home):
            (self.home/'logfile').write_text('Download progress\nProvider failure details\n')
        self.assertIn('Download progress',output.getvalue())
        self.assertIn('Provider failure details',output.getvalue())

    def test_launcher_adapter_preserves_location_and_mirrors_diagnostics(self):
        text = ('#!/bin/bash\nset -Eeuo pipefail\n'
                'SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"\n'
                'LAUNCH_ERROR_LOG=/dev/null\n'
                'echo launcher-diagnostics >"$LAUNCH_ERROR_LOG" 2>&1\n')
        android.LAUNCHER.write_text(text)
        digest = hashlib.sha256(text.encode()).hexdigest()
        with patch.object(android,'LAUNCHER_DIGEST',digest), android._app_launcher() as staged:
            result = subprocess.run([str(staged)],capture_output=True,text=True,check=True)
            self.assertIn('launcher-diagnostics',result.stdout)
            self.assertIn(str(android.LAUNCHER.parent),staged.read_text())
        self.assertEqual(android.LAUNCHER.read_text(),text)

    def test_unsupported_launcher_preserves_image_without_launch(self):
        before = android.IMAGE.read_bytes()
        self.assertEqual(android.retry(),2)
        self.assertEqual(android.IMAGE.read_bytes(),before)
        self.assertFalse((self.home/'launched').exists())

    def test_changed_provider_contract_fails_before_any_provider_execution(self):
        android.CHECKOUT.mkdir(); (android.CHECKOUT/'.git').mkdir()
        script = android.CHECKOUT/'steamos-waydroid-installer.sh'
        script.write_text('#!/bin/bash\nexit 0\n'); script.chmod(0o700)
        with patch.object(android,'_run_provider') as run:
            self.assertEqual(android._run(),2)
            run.assert_not_called()

    def test_adapter_changes_only_authorization_and_keeps_original_checkout(self):
        android.CHECKOUT.mkdir(); (android.CHECKOUT/'.git').mkdir()
        main = android.CHECKOUT/'steamos-waydroid-installer.sh'
        main.write_text('#!/bin/bash\n# compatibility, storage and protected-repair stand-in\n'+android.INSTALLER_ROOT+'\nexit 0\n')
        sanity = android.CHECKOUT/'libexec/steamos-waydroid/installer-sanity-checks.sh'
        sanity.parent.mkdir(parents=True)
        sanity.write_text('run_privileged_sanity_checks() {\n'+android.AUTH_START+
                          "\tprintf '%s\\n' \"$current_password\" | sudo -S -k -v\n"+android.AUTH_END+'\t# preserve Decky checks\n}\n')
        rules = android.CHECKOUT/'extras/zzzzzzzz-waydroid'; rules.parent.mkdir()
        rules.write_text(''.join('deck ALL=(root) NOPASSWD: /usr/bin/'+name+'\n' for name in ('waydroid-startup-scripts','waydroid-shutdown-scripts','waydroid-mount','waydroid-firewall')))
        before = {str(p.relative_to(android.CHECKOUT)):p.read_bytes() for p in android.CHECKOUT.rglob('*') if p.is_file()}
        contract = {str(p.relative_to(android.CHECKOUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (main,sanity)}
        with patch.object(android,'PROVIDER_CONTRACT',contract), patch.object(android.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'test-revision\n')):
            with android._app_provider() as staged:
                staged_main = (staged/main.name).read_text()
                self.assertIn(str(android.CHECKOUT),staged_main)
                self.assertEqual(staged_main.replace(str(android.CHECKOUT),'"$WORKING_DIR"'),main.read_text())
                adapted = (staged/sanity.relative_to(android.CHECKOUT)).read_text()
                self.assertNotIn('read -r -s',adapted); self.assertNotIn('sudo -S -k',adapted)
                self.assertIn('sudo -v',adapted); self.assertIn("current_password=''",adapted)
                self.assertIn('# preserve Decky checks',adapted)
                self.assertNotIn('NOPASSWD', (staged/rules.relative_to(android.CHECKOUT)).read_text())
                temporary = staged
        self.assertFalse(temporary.exists())
        self.assertEqual(before, {str(p.relative_to(android.CHECKOUT)):p.read_bytes() for p in android.CHECKOUT.rglob('*') if p.is_file()})

    def test_queue_calls_android_retry_and_finish_does_not_open_terminal(self):
        row = {'key':'module:android','kind':'module','owner':'android'}
        self.assertFalse(setup_install.interactive_provider(row))
        with patch.object(setup_install,'verify',return_value=False), patch.object(privilege,'command'), patch.object(android,'retry',return_value=0) as retry:
            self.assertIn('verified',setup_install.execute(row)); retry.assert_called_once()
        with patch.object(setup_install,'running',return_value=False), patch.object(setup_finish.setup_plan,'items',return_value=({},[row])), patch.object(setup_finish.subprocess,'Popen') as launch:
            with self.assertRaisesRegex(ValueError,'installation queue'): setup_finish.action(row['key'],'launch')
            launch.assert_not_called()


if __name__ == '__main__': unittest.main()
