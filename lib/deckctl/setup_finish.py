"""Honest post-install readiness and catalog-owned launch actions."""
from pathlib import Path
import subprocess
import hashlib
import json
import shutil
from . import core, setup_plan, setup_install

STEPS = {'module:decky': 'decky', 'module:emulation': 'emudeck', 'module:android': 'android',
         'media:keeper': 'keeper', 'launcher:battlenet': 'battlenet', 'remote:tailscale': 'tailscale'}


def rows():
    confirmations = core.load_json(core.STATE/'setup-confirmations.json', {})
    result = []
    for row in setup_plan.items()[1]:
        if not row['visible']: continue
        installed, evidence = setup_plan.present(row)
        key = row['key']
        followup = row.get('followup', '')
        confirmed = confirmations.get(key) == hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()
        detected = core._codex_logged_in() if key == 'dev:codex' and installed else core._claude_logged_in() if key == 'dev:claude-code' and installed else False
        ready = installed and (not followup or confirmed or detected)
        status = 'Ready' if ready else 'Needs pairing' if installed and followup == 'pairing' else 'Needs sign-in' if installed and followup == 'signin' else 'Needs setup'
        result.append({**row, 'status': status, 'installed': installed,
                       'note': 'Confirmed by you. Recheck after changing this installation.' if ready and confirmed and followup else 'Complete the staged installer, then confirm setup.' if installed and followup == 'setup' else 'Installed; account sign-in is not checked automatically.' if installed and followup and not detected else 'Installation detected.' if installed else 'Complete installation or vendor setup, then recheck.',
                       'canLaunch': bool(key == 'launcher:nonsteamlaunchers' or 'flatpak' in row or key in STEPS or key in ('dev:codex', 'dev:claude-code') or row['owner'] in ('workspace', 'media')),
                       'canConfirm': installed and followup in ('signin', 'pairing', 'setup') and key not in ('dev:codex', 'dev:claude-code')})
    return result


def action(key, operation):
    if setup_install.running(): raise ValueError('Wait for installation to finish first.')
    selected = {row['key']: row for row in setup_plan.items()[1]}
    if key not in selected: raise ValueError('This item is not selected.')
    row = selected[key]
    if operation == 'confirm':
        current = next(item for item in rows() if item['key'] == key)
        if not current['canConfirm']: raise ValueError('This item requires detected readiness or installation first.')
        path = core.STATE/'setup-confirmations.json'
        state = core.load_json(path, {})
        state[key] = hashlib.sha256(json.dumps(setup_plan.present(row)[1], sort_keys=True).encode()).hexdigest()
        core.save_json(path, state)
        return {'confirmed': True}
    if operation != 'launch': raise ValueError('Unknown finish action.')
    if key == 'launcher:nonsteamlaunchers':
        path = Path.home()/'Desktop/Deck-Setup-Staged/NonSteamLaunchers.desktop'
        if not path.is_file() or not core._launch_path(path): raise ValueError('Stage the official installer first.')
        return {'launched': True}
    if key in STEPS:
        command = [str(core.ROOT/'bin/deckctl'), 'setup', 'run', '--step', STEPS[key]]
    elif key in ('dev:codex', 'dev:claude-code'):
        command = [setup_plan.binary('codex' if key == 'dev:codex' else 'claude')]
        if not command[0]: raise ValueError('Install this tool first.')
        logged_in = core._codex_logged_in() if key == 'dev:codex' else core._claude_logged_in()
        if not logged_in: command += ['login'] if key == 'dev:codex' else ['auth', 'login']
    elif 'flatpak' in row:
        subprocess.Popen(['flatpak', 'run', row['flatpak']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {'launched': True}
    elif row['owner'] in ('workspace', 'media') and row.get('component'):
        path = Path.home()/'.local/share/applications'/('deck-'+row['owner']+'-'+row['component']+'.desktop')
        if not path.is_file(): raise ValueError('Create this shortcut first.')
        if not core._launch_path(path): raise ValueError('Could not open the shortcut.')
        return {'launched': True}
    else: raise ValueError('No launch action is available for this item.')
    terminal = shutil.which('konsole')
    if not terminal: raise ValueError('Konsole is required for guided setup.')
    subprocess.Popen([terminal, '--separate', '--nofork', '-e', *command])
    return {'launched': True}
