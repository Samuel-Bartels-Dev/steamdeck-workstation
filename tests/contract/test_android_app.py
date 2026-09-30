#!/usr/bin/env python3
"""Android adapter and queue regressions; no real provider or host changes."""
from contextlib import nullcontext
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
import shlex
import signal
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'lib'))
from deckctl import android, app_sudo, setup_install, setup_finish, privilege, user_session
import test_v0222 as android_fixtures
import test_app_sudo as auth_fixtures


class AndroidApp(unittest.TestCase):
    launcher = android_fixtures.AndroidProvisioning.launcher

    def setUp(self):
        android_fixtures.AndroidProvisioning.setUp(self)
        self.stack.enter_context(patch.dict(os.environ, {'DECKCTL_UI_RUN':'1', 'DECKCTL_APP_SUDO':'test-owner'}))
        self.stack.enter_context(patch.object(user_session, 'nested_desktop', return_value=False))
        self.stack.enter_context(patch.object(android,'RUNTIME_LIBRARY',self.home/'.local/share/steamdeck-workstation/releases/reviewed-fixture/lib'))
        self.release = self.stack.enter_context(patch.object(app_sudo,'release_session',create=True,return_value=0))

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
        with patch.object(android,'_install_launch_wrapper'), patch.object(android,'_app_launcher',side_effect=lambda: nullcontext(android.LAUNCHER)), patch.object(android,'_app_authorization_result',return_value=True):
            self.launcher('echo launcher-output\nexit 0')
            self.assertEqual(android.retry(),2)
            self.launcher('mkdir -p "$HOME/.local/share/waydroid"\nexit 7')
            self.assertEqual(android.retry(),7)

    def test_provider_cannot_report_success_after_suppressing_auth_failure(self):
        with patch.object(android,'_install_launch_wrapper'), patch.object(android,'_app_launcher',side_effect=lambda: nullcontext(android.LAUNCHER)), patch.object(android,'_app_authorization_result',return_value=False):
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

    def test_resolution_adapter_drains_xdpyinfo_and_keeps_real_failures(self):
        fake = self.home/'fake-x11'
        fake.mkdir()
        xdpyinfo = fake/'xdpyinfo'
        xdpyinfo.write_text('#!/usr/bin/python3\nimport os, signal\nsignal.signal(signal.SIGPIPE, signal.SIG_DFL)\n'
                           'os.write(1,b"dimensions: 1280x800 pixels\\n")\n'
                           'for _ in range(1024): os.write(1,b"ignored data"*1024+b"\\n")\n'
                           'os.write(1,b"dimensions: 640x480 pixels\\n")\n')
        xdpyinfo.chmod(0o700)
        native = '#!/bin/bash\nset -Eeuo pipefail\n'+android.RESOLUTION_COMMAND+'\nprintf "%s\\n" "$RESOLUTION"\n'
        android.LAUNCHER.write_text(native)
        digest = hashlib.sha256(native.encode()).hexdigest()
        env = dict(os.environ,PATH=str(fake)+os.pathsep+os.environ['PATH'])
        result = subprocess.run([str(android.LAUNCHER)],capture_output=True,text=True,env=env)
        self.assertEqual(result.returncode,141)
        self.assertEqual(result.stdout,'')
        with patch.object(android,'LAUNCHER_DIGEST',digest), android._app_launcher() as adapted:
            result = subprocess.run([str(adapted)],capture_output=True,text=True,env=env)
            self.assertEqual(result.returncode,0)
            self.assertEqual(result.stdout,'1280x800\n')
            xdpyinfo.write_text('#!/bin/sh\nprintf "dimensions: 1280x800 pixels\\n"\nexit 9\n')
            result = subprocess.run([str(adapted)],capture_output=True,text=True,env=env)
            self.assertEqual(result.returncode,9)
            self.assertEqual(result.stdout,'')
        self.assertEqual(android.LAUNCHER.read_text(),native)
        self.assertEqual(android.IMAGE.read_bytes(),b'preserved image')

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
        launcher = android.CHECKOUT/'extras/scripts/Android_Waydroid_Cage.sh'
        launcher.parent.mkdir(); launcher.write_text('#!/bin/bash\n# pinned launcher\n')
        before = {str(p.relative_to(android.CHECKOUT)):p.read_bytes() for p in android.CHECKOUT.rglob('*') if p.is_file()}
        contract = {str(p.relative_to(android.CHECKOUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (main,sanity,launcher)}
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

    def test_provider_launcher_is_pinned_before_staging_or_execution(self):
        self.assertEqual(android.PROVIDER_CONTRACT['extras/scripts/Android_Waydroid_Cage.sh'], android.LAUNCHER_DIGEST)
        contract = {}
        for relative in android.PROVIDER_CONTRACT:
            source = android.CHECKOUT/relative
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(b'original')
            contract[relative] = hashlib.sha256(b'original').hexdigest()
        (android.CHECKOUT/'extras/scripts/Android_Waydroid_Cage.sh').write_bytes(b'changed launcher')
        with patch.object(android,'PROVIDER_CONTRACT',contract), patch.object(android.shutil,'copytree') as copy, patch.object(android.subprocess,'run') as run:
            with self.assertRaisesRegex(RuntimeError,'contract changed'):
                with android._app_provider(): self.fail('Changed launcher accepted')
            copy.assert_not_called(); run.assert_not_called()

    def test_durable_wrapper_preserves_vendor_bytes_and_launches_without_recursion(self):
        from deckctl import app_sudo
        self.launcher('printf "%s\\n" "$DECKCTL_APP_SUDO" "$DECKCTL_SUDO_KEEP_DESCENDANTS" "$DECKCTL_SUDO_SESSION" "$@" > "$HOME/runtime-args"\nexit 7')
        original = android.LAUNCHER.read_bytes()
        digest = hashlib.sha256(original).hexdigest()
        owner = Mock(); owner.environment.return_value = {'DECKCTL_APP_SUDO':'runtime-owner'}
        before = dict(os.environ)
        with patch.object(android,'LAUNCHER_DIGEST',digest), patch.object(app_sudo,'Owner',return_value=owner), patch.object(privilege.Session,'prepare'), patch.object(android,'_app_authorization_result',return_value=True):
            android._install_launch_wrapper()
            wrapped = android.LAUNCHER.read_bytes()
            android._install_launch_wrapper()
            self.assertEqual(android.LAUNCHER.read_bytes(),wrapped)
            self.assertEqual(android._launcher_source().read_bytes(),original)
            with patch.dict(os.environ):
                os.environ.pop('DECKCTL_APP_SUDO')
                self.assertEqual(android.launch(['com.fixture.game']),7)
            self.assertEqual(android._launcher_source().read_bytes(),original)
        owner.close.assert_called_once()
        values = (self.home/'runtime-args').read_text().splitlines()
        self.assertEqual(values[:2],['runtime-owner','1'])
        self.assertEqual(values[3:],['com.fixture.game'])
        self.assertEqual(self.release.call_args.args,(values[2],))
        self.assertEqual(self.release.call_args.kwargs['env']['DECKCTL_APP_SUDO'],'runtime-owner')
        self.assertEqual(dict(os.environ),before)
        self.assertEqual(android.IMAGE.read_bytes(),b'preserved image')

    def test_wrapper_executes_python_module_and_forwards_package(self):
        fake_library = android.RUNTIME_LIBRARY
        fake_module = fake_library/'deckctl/android.py'
        fake_module.parent.mkdir(parents=True)
        (fake_module.parent/'__init__.py').write_text('')
        fake_module.write_text('import os\nfrom pathlib import Path\ndef launch(args):\n    Path(os.environ["HOME"], "wrapper-args").write_text("\\n".join(args))\n    return 0\n')
        original = android.LAUNCHER.read_bytes()
        with patch.object(android,'LAUNCHER_DIGEST',hashlib.sha256(original).hexdigest()):
            android._install_launch_wrapper()
            subprocess.run([str(android.LAUNCHER),'com.fixture.game'], check=True, env=dict(os.environ))
        self.assertEqual((self.home/'wrapper-args').read_text(),'com.fixture.game')
        self.assertEqual(android.LAUNCHER.with_name('Android_Waydroid_Cage.vendor.sh').read_bytes(),original)

    def test_wrapper_survives_current_rollback_and_refuses_missing_launch_capability(self):
        pinned = android.RUNTIME_LIBRARY/'deckctl'
        pinned.mkdir(parents=True)
        (pinned/'__init__.py').write_text('')
        (pinned/'android.py').write_text('def launch(args):\n    print("pinned-release:"+args[0])\n    return 0\n')
        older = pinned.parents[2]/'older-main'
        older_module = older/'lib/deckctl'
        older_module.mkdir(parents=True)
        (older_module/'__init__.py').write_text('')
        (older_module/'android.py').write_text('# Earlier main has no launch function.\n')
        current = self.home/'.local/share/steamdeck-workstation/current'
        current.symlink_to(older)
        original = android.LAUNCHER.read_bytes()
        with patch.object(android,'LAUNCHER_DIGEST',hashlib.sha256(original).hexdigest()):
            android._install_launch_wrapper()
            result = subprocess.run([str(android.LAUNCHER),'com.fixture.game'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0)
            self.assertEqual(result.stdout,'pinned-release:com.fixture.game\n')
            competing = self.home/'launch-directory/deckctl'
            competing.mkdir(parents=True)
            (competing/'__init__.py').write_text('')
            (competing/'android.py').write_text('def launch(args):\n    raise RuntimeError("wrong runtime")\n')
            result = subprocess.run([str(android.LAUNCHER),'com.fixture.game'],capture_output=True,text=True,cwd=competing.parent)
            self.assertEqual(result.returncode,0)
            self.assertEqual(result.stdout,'pinned-release:com.fixture.game\n')
            (pinned/'android.py').write_text('# Pinned runtime unexpectedly lacks launch.\n')
            result = subprocess.run([str(android.LAUNCHER)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertIn('lacks Android launch support',result.stderr)
        self.assertEqual(current.resolve(),older)
        self.assertEqual(android.LAUNCHER.with_name('Android_Waydroid_Cage.vendor.sh').read_bytes(),original)

    def test_exact_legacy_wrapper_migrates_without_changing_vendor_or_state(self):
        original = android.LAUNCHER.read_bytes()
        vendor = android.LAUNCHER.with_name('Android_Waydroid_Cage.vendor.sh')
        vendor.write_bytes(original)
        android.LAUNCHER.write_text(android._legacy_wrapper_text())
        with patch.object(android,'LAUNCHER_DIGEST',hashlib.sha256(original).hexdigest()):
            android._install_launch_wrapper()
            self.assertEqual(android.LAUNCHER.read_text(),android._wrapper_text())
            self.assertEqual(android._launcher_source(),vendor)
        self.assertEqual(vendor.read_bytes(),original)
        self.assertEqual(android.IMAGE.read_bytes(),b'preserved image')
        self.assertFalse(android.STATE.exists())

    def test_known_pinned_wrapper_migrates_to_new_installed_release(self):
        original = android.LAUNCHER.read_bytes()
        vendor = android.LAUNCHER.with_name('Android_Waydroid_Cage.vendor.sh')
        vendor.write_bytes(original)
        older = android.RUNTIME_LIBRARY.parent.parent/'previous-reviewed/lib'
        android.LAUNCHER.write_text(android._wrapper_text(older))
        with patch.object(android,'LAUNCHER_DIGEST',hashlib.sha256(original).hexdigest()):
            android._install_launch_wrapper()
            self.assertEqual(android.LAUNCHER.read_text(),android._wrapper_text())
            self.assertEqual(android._launcher_source(),vendor)
        self.assertEqual(vendor.read_bytes(),original)

    def test_edited_legacy_wrapper_is_preserved_and_development_runtime_is_refused(self):
        original = android.LAUNCHER.read_bytes()
        vendor = android.LAUNCHER.with_name('Android_Waydroid_Cage.vendor.sh')
        vendor.write_bytes(original)
        edited = android._legacy_wrapper_text()+'# user edit\n'
        android.LAUNCHER.write_text(edited)
        with patch.object(android,'LAUNCHER_DIGEST',hashlib.sha256(original).hexdigest()):
            with self.assertRaisesRegex(RuntimeError,'wrapper was edited'):
                android._install_launch_wrapper()
            with patch.object(android,'RUNTIME_LIBRARY',self.home/'disposable-worktree/lib'):
                with self.assertRaisesRegex(RuntimeError,'persistent installed release'):
                    android._install_launch_wrapper()
        self.assertEqual(android.LAUNCHER.read_text(),edited)
        self.assertEqual(vendor.read_bytes(),original)

    def test_durable_launch_replaces_inherited_stale_transport_and_sudo_path(self):
        stale = self.home/'stale-owner'
        stale.mkdir()
        (stale/'sudo').write_text('#!/bin/sh\nprintf stale-sudo-used > "$HOME/stale-used"\nexit 125\n')
        (stale/'sudo').chmod(0o700)
        fake = self.home/'fake-system'
        fake.mkdir()
        (fake/'sudo').write_text(auth_fixtures.FAKE)
        (fake/'sudo').chmod(0o700)
        self.launcher('printf "%s\\n" "$DECKCTL_APP_SUDO" "${DECKCTL_UI_CONTROL-unset}" > "$HOME/fresh-owner"\nmkdir -p "$HOME/.local/share/waydroid"')
        digest = hashlib.sha256(android.LAUNCHER.read_bytes()).hexdigest()
        inherited = {'DECKCTL_APP_SUDO':str(stale/'socket'), 'DECKCTL_UI_CONTROL':'stale-run',
                     'PATH':str(stale)+os.pathsep+str(fake)+os.pathsep+os.environ['PATH'],
                     'TEST_SUDO_ROOT':str(fake)}
        def authenticate():
            self.assertNotIn('DECKCTL_UI_CONTROL',os.environ)
            self.assertNotIn(str(stale),os.environ['PATH'].split(os.pathsep))
            result = subprocess.run(privilege.command(['-v']),env=privilege.environment(),stdin=subprocess.DEVNULL)
            self.assertEqual(result.returncode,0)
        with patch.dict(os.environ,inherited), patch.object(android,'LAUNCHER_DIGEST',digest), patch.object(privilege.Session,'prepare',side_effect=authenticate):
            before = dict(os.environ)
            self.assertEqual(android.launch(),0)
            self.assertEqual(dict(os.environ),before)
        socket_path, control = (self.home/'fresh-owner').read_text().splitlines()
        self.assertNotEqual(socket_path,str(stale/'socket'))
        self.assertEqual(control,'unset')
        self.assertFalse(Path(socket_path).exists())
        self.assertFalse(list(fake.glob('ticket-*')))
        self.assertFalse((self.home/'stale-used').exists())
        self.assertEqual((fake/'prompts').read_text().splitlines(),['prompt'])

    def test_wrapper_missing_control_plane_is_visible_without_running_vendor(self):
        original = android.LAUNCHER.read_bytes()
        with patch.object(android,'LAUNCHER_DIGEST',hashlib.sha256(original).hexdigest()):
            android._install_launch_wrapper()
            result = subprocess.run([str(android.LAUNCHER)], capture_output=True, text=True)
        self.assertEqual(result.returncode,2)
        self.assertIn('restore the pinned deckctl release',result.stderr)
        self.assertFalse((self.home/'launched').exists())

    def test_launcher_owner_crash_stops_stubborn_gui_standin(self):
        pidfile = self.home/'gui-pid'
        child = ('import os, signal, time; from pathlib import Path; '
                 'signal.signal(signal.SIGTERM,signal.SIG_IGN); '
                 'Path('+repr(str(pidfile))+').write_text(str(os.getpid())); time.sleep(60)')
        android.LAUNCHER.write_text('#!/bin/sh\nexec /usr/bin/python3 -c '+shlex.quote(child)+'\n')
        source = ('import os; from pathlib import Path; from deckctl import android; '
                  'android.LAUNCHER=Path('+repr(str(android.LAUNCHER))+'); '
                  'android._run_app_launcher(android.LAUNCHER,(),dict(os.environ))')
        process = subprocess.Popen([sys.executable,'-B','-c',source],
                                   env=dict(os.environ,PYTHONPATH=str(Path(android.__file__).parents[1])), start_new_session=True)
        self.addCleanup(lambda: process.kill() if process.poll() is None else None)
        deadline = time.monotonic()+5
        while not pidfile.exists() and time.monotonic()<deadline: time.sleep(.05)
        self.assertTrue(pidfile.exists())
        pid = pidfile.read_text()
        os.killpg(process.pid,signal.SIGKILL); process.wait(timeout=5)
        deadline = time.monotonic()+5
        while time.monotonic()<deadline:
            try: state = Path('/proc/'+pid+'/stat').read_text().split()[2]
            except FileNotFoundError: break
            if state == 'Z': break
            time.sleep(.05)
        else: self.fail('Launcher GUI survived owner crash')

    def test_wrapper_refuses_edited_vendor_backup_without_replacing_launcher(self):
        original = android.LAUNCHER.read_bytes()
        backup = android.LAUNCHER.with_name('Android_Waydroid_Cage.vendor.sh')
        backup.write_bytes(b'user recovery file')
        with patch.object(android,'LAUNCHER_DIGEST',hashlib.sha256(original).hexdigest()):
            with self.assertRaisesRegex(RuntimeError,'different content'):
                android._install_launch_wrapper()
        self.assertEqual(android.LAUNCHER.read_bytes(),original)
        self.assertEqual(backup.read_bytes(),b'user recovery file')

    def test_edited_app_wrapper_is_preserved_and_refused(self):
        original = android.LAUNCHER.read_bytes()
        with patch.object(android,'LAUNCHER_DIGEST',hashlib.sha256(original).hexdigest()):
            android._install_launch_wrapper()
            edited = android.LAUNCHER.read_text()+'# user launch change\n'
            android.LAUNCHER.write_text(edited)
            with self.assertRaisesRegex(RuntimeError,'wrapper was edited'):
                android._install_launch_wrapper()
            with self.assertRaisesRegex(RuntimeError,'wrapper was edited'):
                with android._app_launcher(): self.fail('Edited wrapper was accepted')
        self.assertEqual(android.LAUNCHER.read_text(),edited)
        self.assertEqual(android.LAUNCHER.with_name('Android_Waydroid_Cage.vendor.sh').read_bytes(),original)

    def test_durable_launch_rejects_nested_before_authorization(self):
        from deckctl import app_sudo
        with patch.object(user_session,'nested_desktop',return_value=True), patch.object(app_sudo,'Owner') as owner, patch.object(privilege.Session,'prepare') as authorize, patch.object(android,'_first_run') as run:
            self.assertEqual(android.launch(),2)
            owner.assert_not_called(); authorize.assert_not_called(); run.assert_not_called()

    def test_queue_calls_android_retry_and_finish_does_not_open_terminal(self):
        row = {'key':'module:android','kind':'module','owner':'android'}
        self.assertFalse(setup_install.interactive_provider(row))
        with patch.object(setup_install,'verify',return_value=False), patch.object(privilege,'command'), patch.object(android,'retry',return_value=0) as retry:
            self.assertIn('verified',setup_install.execute(row)); retry.assert_called_once()
        with patch.object(setup_install,'running',return_value=False), patch.object(setup_finish.setup_plan,'items',return_value=({},[row])), patch.object(setup_finish.subprocess,'Popen') as launch:
            with self.assertRaisesRegex(ValueError,'installation queue'): setup_finish.action(row['key'],'launch')
            launch.assert_not_called()


if __name__ == '__main__': unittest.main()
