"""Inspect launch targets and offer explicit, backed-up shortcut repairs."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shlex
import shutil
import tempfile
import time
from . import core, desktop, file_state, library

def target_status(executable):
    try:argv=shlex.split(executable or '')
    except ValueError:return 'UNRESOLVED'
    if not argv:return 'MISSING'
    target=Path(argv[0]).expanduser()
    if target.is_absolute():return 'FOUND' if target.is_file() else 'MISSING'
    return 'FOUND' if shutil.which(argv[0]) else 'UNRESOLVED'

def _desktop_rows():
    rows=[]
    roots={desktop.desktop_dir(),Path.home()/'.local/share/applications',Path.home()/'Desktop/Deck-Setup-Staged'}
    for root in sorted(roots):
        for name,icon in desktop.ENTRIES.items():
            path=root/name
            if not path.exists() and not path.is_symlink():continue
            try:
                file_state.no_links(path)
                text=path.read_text();lines=text.splitlines()
                if '[Desktop Entry]' not in lines:raise ValueError('Missing Desktop Entry section')
                start=lines.index('[Desktop Entry]')+1
                end=next((i for i in range(start,len(lines)) if lines[i].startswith('[')),len(lines))
                fields=dict(line.split('=',1) for line in lines[start:end] if '=' in line)
                expected=desktop.icon_path(icon)
                source=core.ROOT/'modules/base/icons'/f'{icon}.svg'
                bad_icon=(fields.get('Icon')!=str(expected) or not expected.is_file() or expected.read_bytes()!=source.read_bytes())
                rows.append({'path':str(path),'icon':icon,'icon_repair':bad_icon or not os.access(path,os.X_OK),
                             'target':target_status(fields.get('Exec',''))})
            except (OSError,ValueError) as exc:rows.append({'path':str(path),'error':str(exc)})
    return rows

def audit(as_json=False):
    entries=library.shortcuts();rows=[];seen={}
    for entry in entries:
        if '_error' in entry:rows.append({'error':entry['_error']});continue
        key=(entry['vdf'],json.dumps({k:v for k,v in entry.items() if k not in ('vdf','user')},sort_keys=True))
        duplicate=key in seen;seen[key]=True
        rows.append({'user':entry['user'],'name':entry['appname'],'vdf':entry['vdf'],
                     'target':target_status(entry.get('exe','')),'exact_duplicate':duplicate,
                     'art':library._art_status(entry)})
    data={'steam':rows,'desktop':_desktop_rows(),'artwork_owner':'SteamGridDB'}
    if as_json:print(json.dumps(data,indent=2))
    else:
        print('SHORTCUT AUDIT')
        for row in rows:
            if 'error' in row:print('ERROR: '+row['error']);continue
            print(f"{row['user']}: {row['name']} — target {row['target']}"+(' — exact duplicate' if row['exact_duplicate'] else ''))
            art=row['art']
            missing=[k for k in ('portrait','wide','hero','logo','icon') if not art.get(k)]
            if missing:print('  SteamGridDB artwork: '+', '.join(missing))
        for row in data['desktop']:print(f"{row['path']}: "+(row.get('error') or f"target {row['target']}; icon {'REPAIR' if row['icon_repair'] else 'OK'}"))
        print('Repair preview: deckctl library repair. Missing targets require their owning app/setup step; no executable paths are guessed.')
        print('Gaming Mode artwork remains owned by SteamGridDB.')
    return data

def _deduplicate_bytes(data):
    """Copy record payload bytes verbatim, retaining unknown fields and artwork IDs."""
    prefix=b'\x00shortcuts\x00'
    if not data.startswith(prefix):raise ValueError('Unsupported shortcuts root')
    pos=len(prefix);records=[];seen=set();removed=0
    while pos<len(data) and data[pos]!=8:
        if data[pos]!=0:raise ValueError('Unsupported shortcuts record')
        _,start=library._cstring(data,pos+1)
        obj,end=library._read_obj(data,start)
        if end<=start or data[end-1]!=8:raise ValueError('Truncated shortcuts record')
        signature=json.dumps(obj,sort_keys=True)
        if signature in seen:removed+=1
        else:seen.add(signature);records.append(data[start:end])
        pos=end
    if data[pos:] not in (b'\x08',b'\x08\x08'):raise ValueError('Unsupported shortcuts trailer')
    if not removed:return data,0
    out=prefix+b''.join(b'\x00'+str(i).encode()+b'\x00'+raw for i,raw in enumerate(records))+data[pos:]
    return out,removed

def _steam_running():
    # Avoid VDF writes while Steam may save its in-memory copy.
    proc=Path('/proc')
    for path in proc.glob('[0-9]*/comm'):
        try:
            if path.read_text().strip().lower() in ('steam','steamwebhelper'):return True
        except OSError:pass
    return False

def repair(yes=False,duplicates=False,user=None):
    data=audit();plans=[]
    for row in data['desktop']:
        if not row.get('error') and row['icon_repair']:plans.append(('icon',Path(row['path']),row['icon']))
    if duplicates:
        paths=sorted({Path(r['vdf']) for r in data['steam'] if not r.get('error') and r['exact_duplicate'] and (user is None or r['user']==user)})
        for path in paths:
            file_state.no_links(path);raw=path.read_bytes();new,count=_deduplicate_bytes(raw)
            if count:plans.append(('duplicates',path,(raw,new,count)))
    print(f'Reviewed repair plan: {len(plans)} file(s). No missing-target replacement or artwork changes.')
    for kind,path,_ in plans:print(f'  {kind}: {path}')
    if not plans:return 0
    if not yes:print('Re-run with --yes to apply this plan; --duplicates explicitly enables exact duplicate removal.');return 2
    if any(kind=='duplicates' for kind,_,_ in plans) and _steam_running():raise ValueError('Exit Steam completely before editing shortcuts; no changes made.')
    # Validate every writable path before taking backups or making changes.
    for kind,path,payload in plans:
        file_state.no_links(path)
        if kind=='icon':file_state.no_links(desktop.icon_path(payload))
    backup=core.STATE/'shortcut-rollback'/str(time.time_ns());backup.mkdir(parents=True)
    for index,(kind,path,payload) in enumerate(plans):
        old=path.read_bytes();shutil.copy2(path,backup/f'{index}-{path.name}')
        if kind=='icon':new=desktop._with_icon(old.decode(),desktop.install_icon(payload)).encode()
        else:
            original,new,count=payload
            if old!=original:raise ValueError(f'Shortcuts changed after preview; retry: {path}')
        fd,tmp=tempfile.mkstemp(prefix='.deckctl-shortcut-',dir=path.parent)
        try:
            with os.fdopen(fd,'wb') as f:f.write(new)
            Path(tmp).chmod(0o755 if kind=='icon' else path.stat().st_mode & 0o777)
            os.replace(tmp,path)
        finally:Path(tmp).unlink(missing_ok=True)
        if path.read_bytes()!=new:raise ValueError(f'Write verification failed: {path}')
    print(f'Repairs verified. Previous files: {backup}')
    return 0
