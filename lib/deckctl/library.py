from __future__ import annotations
import json, os, struct
from pathlib import Path
from . import core

# Minimal Valve binary VDF reader sufficient for shortcuts.vdf auditing.
def _cstring(data, pos):
    end=data.find(b'\x00',pos)
    if end<0: raise ValueError('unterminated string')
    return data[pos:end].decode('utf-8','replace'), end+1

def _read_obj(data,pos):
    out={}
    while pos < len(data):
        typ=data[pos]; pos+=1
        if typ==8: return out,pos
        key,pos=_cstring(data,pos)
        if typ==0:
            val,pos=_read_obj(data,pos)
        elif typ==1:
            val,pos=_cstring(data,pos)
        elif typ==2:
            if pos+4>len(data): raise ValueError('short int32')
            val=struct.unpack_from('<i',data,pos)[0]; pos+=4
        elif typ==3:
            val=struct.unpack_from('<f',data,pos)[0]; pos+=4
        elif typ==7:
            val=struct.unpack_from('<Q',data,pos)[0]; pos+=8
        else:
            raise ValueError(f'unsupported binary VDF type {typ}')
        out[key]=val
    return out,pos

def shortcuts():
    entries=[]
    root=Path.home()/'.local/share/Steam/userdata'
    for vdf in root.glob('*/config/shortcuts.vdf') if root.exists() else []:
        try:
            data=vdf.read_bytes(); obj,_=_read_obj(data,0)
            shortcuts_obj=obj.get('shortcuts',obj)
            for _,rec in shortcuts_obj.items():
                if isinstance(rec,dict) and rec.get('appname'):
                    entries.append({'user':vdf.parents[1].name,'vdf':str(vdf),**rec})
        except Exception as e:
            entries.append({'_error':f'{vdf}: {e}'})
    return entries

def _art_status(entry):
    appid=entry.get('appid')
    if not isinstance(appid,int): return {'resolved':False}
    grid_id=appid & 0xffffffff
    grid=Path(entry['vdf']).parent/'grid'
    exts=('png','jpg','jpeg','webp')
    pats={'portrait':f'{grid_id}p','wide':f'{grid_id}','hero':f'{grid_id}_hero','logo':f'{grid_id}_logo','icon':f'{grid_id}_icon'}
    result={'resolved':True,'grid_id':grid_id,'grid_dir':str(grid)}
    for slot,stem in pats.items(): result[slot]=any((grid/f'{stem}.{e}').exists() for e in exts)
    return result

def audit(as_json=False):
    rows=[]
    for e in shortcuts():
        if '_error' in e:
            rows.append(e); continue
        art=_art_status(e)
        rows.append({'name':e.get('appname'),'appid':e.get('appid'),'exe':e.get('exe'),'art':art})
    if as_json:
        print(json.dumps(rows,indent=2)); return rows
    if not rows:
        print('No non-Steam shortcuts found yet.'); return rows
    print('STEAM NON-STEAM LIBRARY AUDIT')
    for r in rows:
        if '_error' in r: print(f"WARN {r['_error']}"); continue
        art=r['art']; missing=[]
        if art.get('resolved'):
            missing=[k for k in ('portrait','wide','hero','logo','icon') if not art.get(k)]
        print(f"\n{r['name']}  appid={r.get('appid')} grid={art.get('grid_id','?')}")
        print('  artwork: '+('COMPLETE' if not missing and art.get('resolved') else 'missing '+', '.join(missing) if missing else 'unresolved'))
    print('\nFix artwork in Game Mode with Decky -> SteamGridDB -> Change Artwork. deckctl audits; it does not pick arbitrary art automatically.')
    return rows
