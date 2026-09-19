from __future__ import annotations
import json, os, shutil, socket, subprocess, tarfile, tempfile, time
from pathlib import Path
from . import core, file_state

BACKUP_VERSION=2

def _emu_root():
    cfg=core.load_json(core.ROOT/'config/default.json',{}).get('storage',{})
    label=cfg.get('emu_label','DECK-EMU')
    for row in core.storage_health(quiet=True):
        if row.get('label')==label and row.get('mount'):
            p=Path(row['mount'].split(',')[0])/'Emulation'
            if p.exists(): return p
    migration=core.load_json(core.STATE/'emulation-migration.json',{}) or {}
    if migration.get('status')=='VERIFIED':raise ValueError('Recorded Emulation card is not mounted; insert it before backup/restore.')
    internal=Path.home()/'Emulation'
    if internal.is_symlink() and not internal.exists():raise ValueError('Emulation card is missing; insert it before backup/restore.')
    return internal.resolve()

def _steam_grid():
    root=Path.home()/'.local/share/Steam/userdata'
    if not root.exists(): return None
    grids=sorted(root.glob('*/config/grid'))
    return grids[0] if grids else None

def _sources():
    emu=_emu_root(); home=Path.home(); grid=_steam_grid()
    sources={
      'emulation-saves':emu/'saves',
      'emulation-storage':emu/'storage',
      'deckctl-config':home/'.config/deckctl',
      'controller-templates':home/'.local/share/Steam/controller_base/templates',
      'steam-artwork':grid,
    }
    for base in [home/'Games/World of Warcraft', home/'Games/World of Warcraft/_retail_', home/'Games/World of Warcraft/_classic_']:
        if not base.exists(): continue
        for rel,key in [('WTF','wow-wtf'),('Interface/AddOns','wow-addons')]:
            p=base/rel
            if p.exists(): sources.setdefault(key,p)
    return {k:v for k,v in sources.items() if v and v.exists()}

def backup_saves():
    cfg=core.load_json(core.ROOT/'config/default.json',{}); dest=Path(os.path.expanduser(cfg.get('backup',{}).get('destination','~/DeckBackups'))); dest.mkdir(parents=True,exist_ok=True)
    srcs=_sources(); stamp=time.strftime('%Y%m%d-%H%M%S'); out=dest/f'deck-state-v2-{stamp}.tar.gz'
    manifest={'format':BACKUP_VERSION,'created_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'categories':{}}
    with tarfile.open(out,'w:gz') as tf:
        tf.dereference=True
        for cat,src in srcs.items():
            manifest['categories'][cat]={'source':str(src),'arc':f'payload/{cat}'}
            tf.add(src.resolve() if src.is_symlink() else src,arcname=f'payload/{cat}')
        raw=json.dumps(manifest,indent=2).encode(); info=tarfile.TarInfo('deckctl-backup-manifest.json'); info.size=len(raw); info.mtime=int(time.time()); import io; tf.addfile(info,io.BytesIO(raw))
    print(f'Created {out}')
    for cat in srcs: print(f'- {cat}')
    return out

def _latest_backup():
    cfg=core.load_json(core.ROOT/'config/default.json',{}); dest=Path(os.path.expanduser(cfg.get('backup',{}).get('destination','~/DeckBackups')))
    files=sorted(dest.glob('deck-state-v2-*.tar.gz'),key=lambda p:p.stat().st_mtime,reverse=True)
    return files[0] if files else None

def _select(categories):
    defaults=set(categories)
    if shutil.which('kdialog'):
        cmd=['kdialog','--title','Restore Deck State','--separate-output','--checklist','Select backup categories to restore. Existing files are merged/overwritten; replaceable game payloads are not included.']
        for c in categories: cmd += [c,c,'on']
        r=__import__('subprocess').run(cmd,text=True,capture_output=True)
        if r.returncode!=0: return None
        return {x.strip().strip('"') for x in r.stdout.splitlines() if x.strip()}
    print('Available categories:')
    for i,c in enumerate(categories,1): print(f'{i}. {c}')
    ans=input('Restore all? [Y/n] ').strip().lower()
    return defaults if ans not in ('n','no') else set()

def _dest_for(cat,manifest):
    home=Path.home()
    if cat=='emulation-saves': return _emu_root()/'saves'
    if cat=='emulation-storage': return _emu_root()/'storage'
    if cat=='deckctl-config': return home/'.config/deckctl'
    if cat=='controller-templates': return home/'.local/share/Steam/controller_base/templates'
    if cat=='steam-artwork':
        grids=sorted((home/'.local/share/Steam/userdata').glob('*/config'))
        if len(grids)!=1:raise ValueError('Steam artwork restore needs exactly one Steam account; choose an account manually before restoring this category.')
        return grids[0]/'grid'
    if cat in ('wow-wtf', 'wow-addons'):
        relative = Path('WTF') if cat == 'wow-wtf' else Path('Interface/AddOns')
        known = [home/'Games/World of Warcraft'/flavor/relative for flavor in ('', '_retail_', '_classic_')]
        original = Path(manifest['categories'][cat]['source'])
        if original in known: return original
        return home/'DeckRestoreStaging'/cat
    raise ValueError(f'Unsupported backup category: {cat}')


def restore(archive=None, dry_run=False, categories=None, yes=False):
    arc=Path(os.path.expanduser(archive)) if archive else _latest_backup()
    if not arc or not arc.exists(): raise SystemExit('No v2 deckctl backup found. Provide an archive path or create one with `deckctl backup saves`.')
    with tarfile.open(arc,'r:gz') as tf:
        try:
            header=tf.getmember('deckctl-backup-manifest.json')
            if not header.isfile() or header.size > 1024*1024: raise ValueError('Invalid manifest')
            manifest=json.load(tf.extractfile(header))
        except Exception: raise SystemExit('Backup is missing a v2 deckctl manifest; restore it manually or use the matching older release.')
        if manifest.get('format') != BACKUP_VERSION: raise ValueError('Unsupported backup format')
        cats=sorted(manifest.get('categories',{}))
        allowed={'emulation-saves','emulation-storage','deckctl-config','controller-templates','steam-artwork','wow-wtf','wow-addons'}
        if not set(cats) <= allowed: raise ValueError('Unknown backup categories')
        members=tf.getmembers()
        if len(members)>100000 or sum(m.size for m in members)>32*1024**3: raise ValueError('Backup exceeds extraction budget')
        seen=set()
        for m in members:
            path=Path(m.name)
            if path.is_absolute() or '..' in path.parts or '\\' in m.name or not (m.isfile() or m.isdir()) or str(path) in seen:
                raise ValueError(f'Unsafe backup entry: {m.name}')
            seen.add(str(path))
        requested=set(categories) if categories is not None else set(cats)
        if not requested<=set(cats):raise ValueError('Unknown category selection')
        # Preview and validate every selected destination before writing any payload.
        plans=[];space=[]
        for cat in sorted(requested):
            prefix=f'payload/{cat}'
            selected=[m for m in members if m.name==prefix or m.name.startswith(prefix+'/')]
            if not selected or not any(m.name==prefix and m.isdir() for m in selected):raise ValueError(f'Missing category directory: {cat}')
            dest=_dest_for(cat,manifest);file_state.no_links(dest)
            previous=file_state.inventory(dest) if dest.exists() else {}
            size=sum(m.size for m in selected if m.isfile())
            prior_size=sum(v.get('size',0) for v in previous.values())
            plans.append((cat,str(dest),size))
            space.extend([(dest,size),(core.STATE,prior_size),(Path(tempfile.gettempdir()),size)])
        print('RESTORE PREVIEW — close games and applications using these files.')
        for cat,dest,size in plans:print(f'{cat}: {size} bytes -> {dest} (merge; preserve previous files in rollback)')
        file_state.require_space(space)
        if dry_run:return 0
        chosen=requested if yes else _select(sorted(requested))
        if chosen is not None and not chosen <= requested: raise ValueError('Unknown category selection')
        if chosen is None: print('Restore cancelled.'); return 1
        if not chosen: print('Nothing selected.'); return 0
        with tempfile.TemporaryDirectory(prefix='deckctl-restore-') as td:
            tmp=Path(td)
            planned=[]
            for cat in sorted(chosen):
                prefix=f'payload/{cat}'
                selected=[m for m in members if m.name==prefix or m.name.startswith(prefix+'/')]
                if not selected: raise ValueError(f'Missing backup payload: {cat}')
                tf.extractall(tmp,members=selected,filter='data')
                src=tmp/prefix; dest=_dest_for(cat,manifest)
                if not src.is_dir(): raise ValueError(f'Backup category must be a directory: {cat}')
                file_state.no_links(dest)
                if dest.is_symlink() or any(p.is_symlink() for p in dest.rglob('*')):
                    raise ValueError(f'Symlink in restore destination: {dest}')
                if dest.exists() and not dest.is_dir(): raise ValueError(f'Destination must be a directory: {dest}')
                planned.append((cat,src,dest))
            receipt={'archive':str(arc),'status':'RUNNING','categories':[]}
            run_id=str(time.time_ns())
            journal=core.STATE/'restore-rollback'/run_id/'result.json'
            core.save_json(journal,receipt)
            for cat,src,dest in planned:
                if dest.exists():
                    rollback=core.STATE/'restore-rollback'/run_id/cat
                    rollback.parent.mkdir(parents=True,exist_ok=True)
                    if dest.is_dir(): shutil.copytree(dest,rollback)
                    else: shutil.copy2(dest,rollback)
                    print(f'Previous files preserved: {rollback}')
                try:
                    expected=file_state.inventory(src)
                    file_state.atomic_merge(src,dest)
                    mismatch=file_state.differences(expected,file_state.inventory(dest))
                    if mismatch:raise ValueError(f'Restored content mismatch: {mismatch[:5]}')
                    receipt['categories'].append({'category':cat,'destination':str(dest),'status':'VERIFIED'})
                    core.save_json(journal,receipt)
                    print(f'Verified {cat} -> {dest}')
                except Exception as exc:
                    receipt.update(status='FAILED',error=str(exc));core.save_json(journal,receipt)
                    print(f'Restore incomplete. Previous files and results: {journal.parent}')
                    raise
            receipt['status']='VERIFIED';core.save_json(journal,receipt)
    print('Selected backup contents restored and SHA-256 verified.')
    print('Applications are not included in save backups. Run deckctl apply, then deckctl setup run for missing apps/login/pairing.')
    print('Use deckctl verify for current application readiness; restoring settings does not prove authentication.')
    return 0

def health(as_json=False):
    modules={m:core.module_status(m) for m in core.topo(core.enabled_modules())}
    setup=core.setup_state(); latest=_latest_backup(); hardware=core.detect_hardware(); storage=core.storage_health(quiet=True)
    network={'dns':False,'tailscale':False}
    try: socket.getaddrinfo('github.com',443); network['dns']=True
    except Exception: pass
    if shutil.which('tailscale'):
        try: network['tailscale']=subprocess.run(['tailscale','status'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5).returncode==0
        except Exception: pass
    data={'hardware':hardware,'modules':modules,'storage':storage,'setup':setup,'latest_backup':str(latest) if latest else None,'network':network}
    if as_json: print(json.dumps(data,indent=2)); return data
    print('DECKCTL HEALTH')
    b=hardware.get('battery',{}); print(f"Hardware     {hardware.get('model')} SteamOS={hardware.get('is_steamos')}")
    if b: print(f"Battery      charge={b.get('charge_percent')}% health={b.get('health_percent')}%")
    bad=[]
    for m,s in modules.items():
        st=s.get('status'); print(f"{m:<13} {st:<17} {s.get('message','')}")
        if st in ('FAILED','NOT_INSTALLED'): bad.append(m)
    print(f"Guided setup completed={len(setup.get('completed',[]))} skipped={len(setup.get('skipped',[]))}")
    print(f"Latest backup {latest or 'NONE'}")
    print(f"Network       DNS={'PASS' if network['dns'] else 'WARN'} Tailscale={'PASS' if network['tailscale'] else 'WARN'}")
    print('RESULT       '+('HEALTHY / REVIEW CONFIG_REQUIRED ITEMS' if not bad else 'ATTENTION REQUIRED: '+', '.join(bad)))
    return data
