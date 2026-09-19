from __future__ import annotations
import json, os, shutil, subprocess, time
from pathlib import Path
from . import core, file_state

def _emu_mount():
    cfg=core.load_json(core.ROOT/'config/default.json',{}).get('storage',{})
    label=cfg.get('emu_label','DECK-EMU')
    for row in core.storage_health(quiet=True):
        if row.get('label')==label and row.get('mount'):
            return Path(row['mount'].split(',')[0]), label
    return None,label

def _current_root():
    mount,_=_emu_mount()
    if mount and (mount/'Emulation').exists(): return mount/'Emulation'
    if (Path.home()/'Emulation').exists(): return Path.home()/'Emulation'
    return None

def migration_status():
    mount,label=_emu_mount(); internal=Path.home()/'Emulation'; target=(mount/'Emulation') if mount else None
    print('EMUDECK STORAGE MIGRATION')
    print(f'{label:<18} {str(mount) if mount else "NOT MOUNTED"}')
    print(f'Internal source    {"FOUND" if internal.exists() else "not present"}  {internal}')
    print(f'Target Emulation   {"FOUND" if target and target.exists() else "not present"}  {target or "-"}')
    state=core.load_json(core.STATE/'emulation-migration.json',{}) or {}
    if state: print(f"Last migration plan {state.get('planned_at','?')} -> {state.get('target','?')}")

def _launch_emudeck():
    app=Path.home()/'Applications/EmuDeck.AppImage'
    if app.is_file() and os.access(app,os.X_OK):
        subprocess.Popen([str(app)]);return True
    # A staged installer is not the installed manager and must not be rerun for migration.
    return False

def migrate_emulation():
    mount,label=_emu_mount(); source=Path.home()/'Emulation'
    if not mount: raise SystemExit(f'{label} is not mounted. Insert/format/label the permanent emulation microSD first.')
    target=mount/'Emulation'
    if source.is_symlink():
        if source.resolve()!=target.resolve():raise ValueError('Existing Emulation link points elsewhere; source unchanged.')
        print('Emulation already uses the selected card.');return 0
    if target.exists() and not source.exists():
        print('Emulation tree is already on the DECK-EMU card. Run migration-status/verify and rerun Steam ROM Manager if needed.'); return 0
    if not source.exists() and not target.exists(): raise SystemExit('No internal Emulation folder found to migrate.')
    expected=file_state.inventory(source)
    actual=file_state.inventory(target) if target.exists() else {}
    pending=sum(v.get('size',0) for n,v in expected.items() if actual.get(n)!=v)
    file_state.require_space([(mount,pending)])
    state={'inventory':expected,'planned_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'source':str(source),'target':str(target),'label':label}
    core.save_json(core.STATE/'emulation-migration.json',state)
    guide=Path.home()/'Desktop/EmuDeck Migration.txt'; guide.parent.mkdir(parents=True,exist_ok=True)
    guide.write_text(f'''EMUDECK MIGRATION\n=================\nSource: {source}\nTarget: {target}\n\nUse EmuDeck's supported Migrate Installation workflow.\n1. Open EmuDeck in Desktop Mode.\n2. Choose Migrate Installation (or re-run Custom Mode if your EmuDeck version routes migration there).\n3. Select the {label} card ({mount}).\n4. Let EmuDeck copy/reconfigure the installation.\n5. Re-run Steam ROM Manager so shortcuts point to the new location.\n6. Run: deckctl storage migration-status\n7. Run: deckctl verify\n\nDo NOT delete {source} yet. EmuDeck intentionally preserves the original until you verify saves, BIOS and ROMs.\n''')
    print(guide)
    if _launch_emudeck(): print('EmuDeck launched. Follow the migration guide on your Desktop.')
    else: print('Could not launch EmuDeck automatically; open it in Desktop Mode and use Migrate Installation.')
    return 0

def verify_migration(as_json=False):
    mount,label=_emu_mount();source=Path.home()/'Emulation'
    state=core.load_json(core.STATE/'emulation-migration.json',{}) or {}
    target=mount/'Emulation' if mount else None
    result={'status':'CONFIG_REQUIRED','target':str(target) if target else None,'issues':[]}
    if not target or not target.is_dir():result['issues'].append(f'{label} is not mounted or its Emulation folder is missing.')
    else:
        try:
            actual=file_state.inventory(target)
            if not all((target/n).is_dir() for n in ('roms','bios')):raise ValueError('Target needs roms and bios directories.')
            if source.is_symlink():
                if source.resolve()!=target.resolve():raise ValueError('Internal Emulation link points to a different location.')
                expected=state.get('inventory')
            elif source.is_dir():expected=file_state.inventory(source)
            else:expected=state.get('inventory')
            if expected is None:raise ValueError('No preserved source or pre-migration inventory; content equivalence cannot be verified.')
            if state.get('target') and Path(state['target'])!=target:raise ValueError('Mounted target differs from the recorded migration plan.')
            mismatch=file_state.differences(expected,actual)
            if mismatch:raise ValueError('Missing or changed files/directories: '+', '.join(mismatch[:12]))
            result.update(status='VERIFIED',verified_entries=len(expected),inventory=expected)
        except (ValueError,OSError) as exc:result['issues'].append(str(exc))
    display={k:v for k,v in result.items() if k!='inventory'}
    if as_json:print(json.dumps(display,indent=2))
    else:
        print('EMULATION MIGRATION: '+result['status'])
        for issue in result['issues']:print(issue)
        if result['status']=='VERIFIED':print('Every preserved source entry matches the destination; extra destination files are retained.')
    return result

def finalize_emulation(yes=False):
    mount,label=_emu_mount();source=Path.home()/'Emulation';target=mount/'Emulation' if mount else None
    if not target or not target.is_dir():raise ValueError(f'No migrated Emulation tree on {label}; source unchanged.')
    if source.is_symlink():
        if source.resolve()!=target.resolve():raise ValueError('Existing Emulation link points somewhere else; left unchanged.')
        # Never rename a previously completed vendor migration link.
        print('Emulation is already redirected; leaving the existing path intact.')
        return 0
    result=verify_migration()
    if result['status']!='VERIFIED':return 2
    if not source.exists():print('Internal source absent; nothing to switch.');return 0
    if not yes:
        print('Re-run with --yes to preserve the internal folder as rollback and link Emulation to the verified card.')
        return 2
    rollback=Path.home()/f'Emulation.pre-deckctl-{time.time_ns()}'
    source.rename(rollback)
    try:source.symlink_to(target,target_is_directory=True)
    except Exception:
        rollback.rename(source);raise
    state=core.load_json(core.STATE/'emulation-migration.json',{}) or {}
    state.update(status='VERIFIED',target=str(target),rollback=str(rollback),inventory=result['inventory'])
    core.save_json(core.STATE/'emulation-migration.json',state)
    print(f'Emulation redirected to {target}; original retained at {rollback}')
    print('Launch emulators and check saves before considering manual removal of the rollback copy.')
    return 0
