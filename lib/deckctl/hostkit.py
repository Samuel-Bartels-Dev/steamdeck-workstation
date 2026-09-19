from __future__ import annotations
import json, shutil, time, zipfile, re, tempfile
from pathlib import Path
from . import core

def build(name, out=None):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
        raise SystemExit("Host name must be a single safe filename component")
    host=core.host_registry().get(name)
    if host is None: raise SystemExit(f"Unknown host: {name}")
    src=core.ROOT/'host/windows'
    if not src.exists(): raise SystemExit('Windows host-kit payload missing from release')
    outdir=Path(out).expanduser() if out else Path.home()/'DeckExports'
    outdir.mkdir(parents=True,exist_ok=True)
    core.STATE.mkdir(parents=True, exist_ok=True)
    work=Path(tempfile.mkdtemp(prefix='host-kit-',dir=core.STATE))
    shutil.copytree(src,work,dirs_exist_ok=True)
    data={'name':name,'generated_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),'target':host.get('target'),'mac':host.get('mac'),'sunshine_port':host.get('sunshine_port',47984)}
    (work/'host.json').write_text(json.dumps(data,indent=2)+'\n')
    zpath=outdir/f'deckctl-sunshine-host-{name}.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
        for p in work.rglob('*'):
            if p.is_file(): z.write(p,p.relative_to(work))
    shutil.rmtree(work)
    print(zpath)
    print('This kit is for the WINDOWS HOST. It is never executed by Steam Deck install.sh.')
    return zpath
