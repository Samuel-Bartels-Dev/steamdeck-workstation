#!/usr/bin/env python3
"""Behavioral/static guardrails for features that have regressed during 0.2.x.

These tests intentionally assert user-visible contracts, not implementation style.
If a feature is intentionally redesigned, update the contract and changelog together.
"""
from __future__ import annotations
import os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
errors=[]

def need(cond, msg):
    if not cond: errors.append(msg)

def isolated_env(home):
    # HOME alone does not isolate explicit deckctl/XDG paths from an installed host.
    env = os.environ.copy()
    env.update({'HOME': str(home), 'PYTHONPATH': str(ROOT/'lib'),
                'DECKCTL_CONFIG': str(home/'config'), 'DECKCTL_STATE': str(home/'state'),
                'XDG_CONFIG_HOME': str(home/'.config'), 'XDG_DATA_HOME': str(home/'.local/share'),
                'XDG_STATE_HOME': str(home/'.local/state'), 'XDG_CACHE_HOME': str(home/'.cache'),
                'PYTHONDONTWRITEBYTECODE': '1'})
    return env

def text(rel):
    p=ROOT/rel
    need(p.exists(), f"missing regression-contract file: {rel}")
    return p.read_text(errors='replace') if p.exists() else ""

core=text('lib/deckctl/core.py')
cli=text('lib/deckctl/cli.py')
decky_install=text('modules/decky/install.sh')
media=text('modules/media/setup-media.sh')
terminal=text('lib/deckctl/terminal.py')
reliability=text('lib/deckctl/reliability.py')
hostkit=text('lib/deckctl/hostkit.py')
controller=text('lib/deckctl/controller.py')
aliases=text('config/aliases.json')

# Persistent command/bootstrap contract.
need('.local/bin/deckctl' in (text('install.sh')+core), 'persistent ~/.local/bin/deckctl install contract missing')
need('def _deckctl_executable' in core, 'guided commands must resolve an absolute persistent/repo-local deckctl path')

# Decky: strict Loader detection and Store-artifact reconciliation.
need('"detect":lambda: _decky_loader_present()' in core, 'Decky guided step must use strict loader detector')
need('(Path.home()/"homebrew").exists() or' not in core, 'bare ~/homebrew must never count as Decky installed')
need('if not _decky_loader_present()' in core and 'def _decky_selected_all_installed' in core, 'plugin completion must require Decky Loader')
need('ORPHANED' in core, 'dplugins must expose orphaned plugin folders when Loader is absent')
need('write_text' not in decky_install and 'cat > "$HOME/Desktop/Decky Selected Plugins.txt"' not in decky_install, 'Decky module must not generate legacy Desktop selection checklist')
need('cat > "$stage/DECKY-PLUGINS.txt"' not in decky_install, 'Decky module must not generate legacy staged checklist')
need('STORE_API' in text('lib/deckctl/decky_installer.py') and 'install_selected' in text('lib/deckctl/decky_installer.py'), 'automated trusted Decky Store installer missing')
need('plugin.json' in text('lib/deckctl/decky_installer.py') and 'dist/index.js' in text('lib/deckctl/decky_installer.py'), 'Decky ZIP structure validation missing')


# Battle.net: choosing it must invoke NSL's targeted launcher-name CLI path, never the full picker.
launcher_mod=text('lib/deckctl/launchers.py')
battle_script=text('modules/gaming/install-battlenet.sh')
need('"Battle.net"' in battle_script, 'Battle.net installer must pass the exact NSL launcher-name argument')
need('install-battlenet.sh' in core, 'guided Battle.net step must launch targeted installer')
need('_launch_path(stage/"NonSteamLaunchers.desktop")' not in core, 'guided Battle.net step must not open generic NSL launcher picker')
need('battlenet_installed' in core and 'Battle.net Launcher.exe' in launcher_mod, 'Battle.net completion must verify the real installed executable')
need("choices=['battlenet']" in cli and 'launchers.install_battlenet' in cli, 'deckctl launcher install battlenet command missing')

# Dynamic Battle.net detection smoke tests.
with tempfile.TemporaryDirectory(prefix='deckctl-battlenet-') as td:
    home=Path(td)
    env=isolated_env(home)
    # A staged generic NSL desktop helper is not installation proof.
    staged=home/'Desktop/Deck-Setup-Staged/NonSteamLaunchers.desktop'; staged.parent.mkdir(parents=True); staged.write_text('[Desktop Entry]\n')
    r=subprocess.run([sys.executable,'-c','from deckctl.launchers import battlenet_installed; print(battlenet_installed())'],cwd=ROOT,env=env,text=True,capture_output=True)
    need(r.stdout.strip()=='False', 'staged NSL helper must not count as Battle.net installed')
    shared=home/'.local/share/Steam/steamapps/compatdata/NonSteamLaunchers/pfx/drive_c/Program Files (x86)/Battle.net/Battle.net Launcher.exe'
    shared.parent.mkdir(parents=True); shared.write_text('fake')
    r=subprocess.run([sys.executable,'-c','from deckctl.launchers import battlenet_installed; print(battlenet_installed())'],cwd=ROOT,env=env,text=True,capture_output=True)
    need(r.stdout.strip()=='True', 'shared NSL Battle.net prefix must be detected')

# Desktop/Game Mode boundary + controller inline reconciliation.
need('"noninteractive":True' in core and 'controller' in core, 'controller-template guided step must be noninteractive')
need('No restart is required during the initial Desktop Mode setup.' in controller, 'controller fresh-setup restart guidance regression')
need('No deckctl terminal commands are required in Game Mode.' in core, 'Game Mode must not instruct users to run deckctl')

# Media/Keeper contract: clean kiosk tiles, persistent Chrome profile, Keeper helper.
need('--kiosk' in media, 'media shortcuts must remain Chrome kiosk-mode')
need('Keeper' in core and 'KEEPER_EXTENSION_ID' in core, 'Keeper Chrome integration missing')
need('def _media_desktop_provisioned' in core, 'media guided completion must distinguish Desktop provisioning from Steam refresh')
need('PENDING STEAM REFRESH' in core and 'waiting for Steam refresh' in media, 'media pending-Steam-refresh state missing')
need('submitted/$sid' in media, 'media submission receipts missing; repeated shortcut submissions can regress')
# Media setup must run inline/bounded and must never fall through to unrelated hardware/update work.
media_block=core[core.find('def media_setup():'):core.find('KEEPER_EXTENSION_ID')]
need('_launch_terminal_command' not in media_block and 'subprocess.run' in media_block, 'media setup must run inline, not in a keep-open Konsole')
need('bios' not in media.lower() and 'firmware' not in media.lower(), 'media helper must not invoke BIOS/firmware workflows')

# Terminal/tmux contract.
for token in ('oh-my-posh','starship','zoxide','fzf','eza','bat','fastfetch','tmux'):
    need(token in terminal.lower(), f'terminal managed tool missing: {token}')
need('set -g prefix C-a' in text('modules/terminal/tmux.conf'), 'tmux Deck-friendly prefix/config missing')
need('dtermux' in aliases, 'tmux alias missing')
need((ROOT/'modules/terminal/bubble-gum-rave.omp.json').exists(), 'Oh My Posh Bubble Gum Rave theme missing')
need('prompt use' in text('modules/terminal/README.md') and 'prompt_use' in terminal, 'prompt-engine switch contract missing')
need('oh-my-posh init bash --strict' in text('modules/terminal/terminal.sh'), 'Oh My Posh Bash initialization missing')
need('dposh' in aliases and 'dstarship' in aliases, 'prompt engine aliases missing')


# Fastfetch archives may contain duplicate basename matches; prefer canonical runtime payload.
need('usr/bin/fastfetch' in terminal, 'fastfetch installer must prefer canonical usr/bin/fastfetch payload')
need('(\"--version\",)' in terminal and 'Installed {binary} failed verification' in terminal, 'fastfetch install must execute post-install version verification')
with tempfile.TemporaryDirectory(prefix='deckctl-fastfetch-') as td:
    code = "\n".join([
        "from deckctl import terminal",
        "import io, tarfile",
        "buf=io.BytesIO()",
        "tf=tarfile.open(fileobj=buf, mode='w:gz')",
        "payloads=[('fastfetch-linux-amd64/usr/bin/fastfetch',b'canonical'),('debug/root/usr/bin/fastfetch',b'debug')]",
        "for name,payload in payloads:\n    info=tarfile.TarInfo(name); info.size=len(payload); info.mode=0o755; tf.addfile(info,io.BytesIO(payload))",
        "tf.close(); buf.seek(0)",
        "tf=tarfile.open(fileobj=buf, mode='r:gz')",
        "chosen=terminal._select_archive_binary(list(tf.getmembers()),'fastfetch',('usr/bin/fastfetch',))",
        "print(chosen.name)",
    ])
    env=isolated_env(Path(td))
    r=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,text=True,capture_output=True)
    need(r.returncode==0, f'fastfetch archive-selection smoke test failed: {r.stderr.strip()}')
    need(r.stdout.strip()=='fastfetch-linux-amd64/usr/bin/fastfetch', 'fastfetch installer must select canonical runtime binary when duplicate basenames exist')

# Reliability/lifecycle contract.
for token in ('css_profile_capture','ui_safe','post_update','profile_export','profile_import','support_bundle'):
    need(token in reliability, f'reliability feature missing: {token}')
need("update'" in cli or 'update"' in cli, 'deckctl update command missing')
need('rollback' in cli and 'rollback' in reliability, 'self-update rollback missing')

# Storage/controller/library/network/host-kit surface stays present.
for cmd in ('migrate-emulation','library','network','health','controller'):
    need(cmd in cli, f'CLI surface regressed: {cmd}')
need((ROOT/'host/windows/Setup-SunshineHost.ps1').exists() and (ROOT/'host/windows/Test-SunshineHost.ps1').exists(), 'Windows Sunshine host kit missing')
# Windows host kit must remain outside Deck module graph.
for manifest in (ROOT/'modules').glob('*/module.json'):
    need('host/windows' not in manifest.read_text(errors='ignore'), f'Windows host kit leaked into Deck module graph: {manifest}')

# Dynamic Decky orphan-state smoke test in an isolated HOME.
with tempfile.TemporaryDirectory(prefix='deckctl-regression-') as td:
    home=Path(td)
    env=isolated_env(home)
    # Create a fake plugin folder but no Loader. It must be ORPHANED, never INSTALLED.
    plug=home/'homebrew/plugins/SDH-CssLoader'; plug.mkdir(parents=True)
    (plug/'plugin.json').write_text('{"name":"CSS Loader"}')
    # This is a presentation test with an explicitly absent Loader. The actual
    # service detector is tested separately with enabled/disabled/error fixtures;
    # changing HOME cannot hide systemctl's host-wide plugin_loader.service.
    code = """from deckctl import core
from unittest.mock import patch
with patch.object(core, '_decky_loader_present', return_value=False):
    core.decky_plugins()
"""
    r=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,text=True,capture_output=True)
    need(r.returncode==0, f'decky orphan-state smoke test failed to run: {r.stderr.strip()}')
    need('ORPHANED' in r.stdout, 'orphan plugin folder must report ORPHANED when Decky Loader is absent')
    need('Decky loader: NOT INSTALLED / NOT DETECTED' in r.stdout, 'missing Decky Loader must be explicit in dplugins')

# Android must verify real image + user state and expose retry/repair commands.
android_verify=text('modules/android/verify.sh')
need('Android_Waydroid/waydroid.img' in android_verify and '.local/share/waydroid' in android_verify, 'Android readiness must require image plus user state')
need("sp.add_parser('android'" in cli and "args.cmd=='android'" in cli and 'android.retry()' in cli, 'first-class Android retry/repair CLI missing')
need('Android 13 with Google Play' in core, 'guided Android recommendation must remain Android 13 with Google Play')
need('Common workflows:' in cli and 'Command groups:' in cli and 'deckctl android retry' in cli, 'rich deckctl -h formatting regressed')
need("sp.add_parser('workspace'" in cli and 'workspace.notion_mcp' in cli, 'workspace/Notion MCP CLI surface missing')
need((ROOT/'modules/workspace/module.json').exists(), 'workspace module missing')


# Waydroid install completion must not be owned by a synchronous Steam shortcut URI.
android_py=text('lib/deckctl/android.py')
need('_write_nonblocking_steam_shim' in android_py and 'setsid -f' in android_py,
     'Waydroid Steam shortcut submission must remain detached/non-blocking')
need("'PENDING_STEAM_REFRESH'" in android_py and 'Steam shortcut visibility is deliberately NOT part of Android readiness' in android_py,
     'Android readiness must remain independent of Steam shortcut refresh')
# Behavioral smoke test: the shim must return immediately even when the real helper blocks.
with tempfile.TemporaryDirectory(prefix='deckctl-waydroid-shim-') as td:
    root=Path(td); shimdir=root/'shim'; shimdir.mkdir()
    real=root/'steamos-add-to-steam-real'
    real.write_text('#!/usr/bin/env bash\nsleep 2\nprintf done > "$1.marker"\n')
    real.chmod(0o755)
    code="""from deckctl.android import _write_nonblocking_steam_shim
from pathlib import Path
import subprocess, sys, time
root=Path(sys.argv[1]); shim=_write_nonblocking_steam_shim(root/'shim', str(root/'steamos-add-to-steam-real'))
t=time.monotonic(); r=subprocess.run([str(shim), str(root/'shortcut')]); print(r.returncode, time.monotonic()-t)
"""
    env=isolated_env(Path(td))
    r=subprocess.run([sys.executable,'-c',code,str(root)],cwd=ROOT,env=env,text=True,capture_output=True)
    need(r.returncode==0, f'Waydroid shortcut shim smoke test failed: {r.stderr.strip()}')
    if r.returncode==0:
        try: elapsed=float(r.stdout.split()[1])
        except Exception: elapsed=99
        need(elapsed < 1.0, 'Waydroid shortcut shim blocked on Steam helper instead of detaching')

if errors:
    print('REGRESSION GUARDRAILS FAILED')
    for e in errors: print('-',e)
    sys.exit(1)
print('REGRESSION GUARDRAILS PASS')
