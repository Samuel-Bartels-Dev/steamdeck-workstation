"""Read release data without executing candidate code or changing desired state."""
from __future__ import annotations
import hashlib
import json
import tempfile
from pathlib import Path
from . import core

def _files(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file() and not p.is_symlink()
            and not any(x in {'.git','__pycache__','release'} for x in p.relative_to(root).parts)
            and p.suffix not in ('.pyc','.pyo')}

def compare(candidate,previous=None):
    from . import reliability
    candidate=Path(candidate)
    if not (candidate/'VERSION').is_file():raise ValueError('Candidate VERSION missing')
    if previous is None:previous=reliability.CURRENT_LINK.resolve() if reliability.CURRENT_LINK.exists() else None
    old=Path(previous) if previous else None
    oldfiles=_files(old) if old and old.exists() else {}
    newfiles=_files(candidate)
    manifest=core.load_json(candidate/'modules/decky/plugins.json',{})
    state=core.load_json(core._decky_selection_path(),{}) or {}
    revision=state.get('manifest_schema_version',0)
    if not isinstance(revision,int):revision=0
    current=set(state.get('selected_folders',core._decky_default_selection()))
    additions=set()
    for upgrade in manifest.get('selection_upgrades',[]):
        if revision<upgrade['manifest_schema_version']:additions.update(upgrade['add_folders'])
    items={i['folder']:i['name'] for cat in ('core','recommended','optional','avoid_by_default') for i in manifest.get(cat,[])}
    modules=core.load_json(candidate/'config/default.json',{}).get('modules',{})
    data={'from':(old/'VERSION').read_text().strip() if old and (old/'VERSION').exists() else None,
          'to':(candidate/'VERSION').read_text().strip(),
          'added_files':sorted(set(newfiles)-set(oldfiles)),
          'changed_files':sorted(n for n in newfiles if n in oldfiles and newfiles[n]!=oldfiles[n]),
          'removed_release_files':sorted(set(oldfiles)-set(newfiles)),
          'decky_additions':[items.get(x,x) for x in sorted(additions-current)],
          'preserved':['User settings, saves and credentials','Existing Decky/CSS settings and unselected plugins','Previous persistent releases for rollback'],
          'attention':['Vendor downloads require internet.','Account login/pairing may require user interaction.','Control-plane update does not itself provision changed modules; run deckctl apply then deckctl setup run.'],
          'modules':sorted(modules)}
    return data

def show(candidate,previous=None,as_json=False):
    data=compare(candidate,previous)
    if as_json:print(json.dumps(data,indent=2))
    else:
        print(f"\nUPGRADE PREVIEW: {data['from'] or 'fresh setup'} -> {data['to']}")
        for key,title in [('added_files','Add'),('changed_files','Change'),('removed_release_files','Remove from new release')]:
            print(f"{title}: {len(data[key])} files")
            for name in data[key]:print('  '+name)
        print('New Decky selections: '+(', '.join(data['decky_additions']) or 'none'))
        for name in data['preserved']:print('Preserve: '+name)
        for note in data['attention']:print('Attention: '+note)
    return data

def preview(archive=None,source=None,as_json=False):
    if source:show(Path(source),as_json=as_json);return 0
    if not archive:raise ValueError('Provide --archive FILE or --source DIRECTORY')
    from . import reliability
    with tempfile.TemporaryDirectory(prefix='deckctl-preview-') as tmp:
        root=reliability._extract_release(Path(archive).expanduser(),Path(tmp))
        show(root,as_json=as_json)
    return 0
